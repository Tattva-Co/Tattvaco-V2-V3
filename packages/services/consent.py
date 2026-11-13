"""Performer registry, consent and the voice-profile consent gate (D4, TFD-CNS-001/002/
004/005; architecture doc docs/architecture/CHARACTER_AND_DIGITAL_HUMAN_ARCHITECTURE.md
§6). Performer/consent *creation* is blocked with 403 ``policy_pending`` while DEC-007
(retention) and DEC-012 (consent template) remain open (AT-CNS-002.2) -- see
``packages.core.config.Settings.consent_policy_approved``. This is the only place
likeness/body/voice data creation is gated; every caller elsewhere (CharacterService,
MeasurementService) calls ``ConsentService.evaluate`` rather than re-implementing the
check.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import List

from sqlalchemy.orm import Session

from packages.core.config import get_settings
from packages.domain.enums import ApprovalDecision, AuditAction, ConsentStatus
from packages.domain.errors import (
    ConsentRequiredError,
    InvalidStateError,
    PolicyPendingError,
    ValidationFailure,
)
from packages.persistence.models import (
    ApprovalRequestModel,
    PerformerConsentModel,
    PerformerModel,
    VoiceProfileModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    PerformerConsentRepository,
    PerformerRepository,
    ProjectRepository,
    VoiceProfileRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext
from packages.services.script_review import record_decision

#: C8's generalized approval target, used the same way D2's screenplay_lock and D4's own
#: character_version decisions use it -- decided through ConsentService.decide_consent,
#: never through the generic POST /approvals/{id}/decide (apps/api/routers/approvals.py's
#: scope-dispatch else branch already 422s any scope it doesn't recognise, per DEC-049).
PERFORMER_CONSENT_TARGET_TYPE = "performer_consent"
PERFORMER_CONSENT_APPROVAL_SCOPE = "performer_consent_decision"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class PerformerService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.performers = PerformerRepository(db)
        self.authz = AuthzService(db)
        self.audit = AuditRepository(db)

    def create_performer(self, actor: ActorContext, project_id: str, display_name: str, notes: str | None = None) -> PerformerModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "consent.manage", project)
        if not get_settings().consent_policy_approved:
            raise PolicyPendingError()
        if not display_name.strip():
            raise ValidationFailure("display_name is required.")

        performer = self.performers.add(
            PerformerModel(
                organization_id=project.organization_id,
                display_name=display_name.strip(),
                notes=notes,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.PERFORMER_CREATED,
            target_type="performer",
            target_id=performer.id,
            details={"display_name": performer.display_name},
        )
        self.db.commit()
        return performer

    def list_performers(self, actor: ActorContext, project_id: str) -> List[PerformerModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.performers.list_for_org(project.organization_id)


@dataclass
class ConsentEvaluation:
    allowed: bool
    reason: str | None = None


class ConsentService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.performers = PerformerRepository(db)
        self.consents = PerformerConsentRepository(db)
        self.approvals = ApprovalRepository(db)
        self.authz = AuthzService(db)
        self.audit = AuditRepository(db)

    def create_consent(
        self,
        actor: ActorContext,
        project_id: str,
        performer_id: str,
        purpose: str,
        *,
        project_scope: List[str] | None = None,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        document_asset_id: str | None = None,
        template_version: str | None = None,
    ) -> tuple[PerformerConsentModel, ApprovalRequestModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "consent.manage", project)
        if not get_settings().consent_policy_approved:
            raise PolicyPendingError()
        if not purpose.strip():
            raise ValidationFailure("purpose is required.")
        performer = self.performers.get_scoped(performer_id, actor.org_id)

        consent = self.consents.add(
            PerformerConsentModel(
                organization_id=project.organization_id,
                performer_id=performer.id,
                version=1,
                purpose=purpose,
                project_scope=project_scope,
                status=ConsentStatus.DRAFT.value,
                recorded_by=actor.user_id,
                valid_from=valid_from,
                valid_until=valid_until,
                document_asset_id=document_asset_id,
                template_version=template_version,
            )
        )
        approval = self.approvals.add(
            ApprovalRequestModel(
                target_type=PERFORMER_CONSENT_TARGET_TYPE,
                target_id=consent.id,
                project_id=project.id,
                organization_id=project.organization_id,
                scope=PERFORMER_CONSENT_APPROVAL_SCOPE,
                candidate_summary={"performer_id": performer.id, "purpose": purpose},
            )
        )
        consent.approval_request_id = approval.id
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CONSENT_DRAFTED,
            target_type="performer_consent",
            target_id=consent.id,
            details={"performer_id": performer.id, "purpose": purpose},
        )
        self.db.commit()
        return consent, approval

    def decide_consent(
        self, actor: ActorContext, project_id: str, consent_id: str, decision: ApprovalDecision, notes: str | None = None
    ) -> PerformerConsentModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "consent.manage", project)
        consent = self.consents.get_scoped(consent_id, actor.org_id)
        if consent.status != ConsentStatus.DRAFT.value:
            raise InvalidStateError(f"Consent '{consent_id}' is not awaiting review.")
        approval = self.approvals.get_pending_for_target(PERFORMER_CONSENT_TARGET_TYPE, consent.id)
        if approval is None:
            raise InvalidStateError(f"No pending approval for consent '{consent_id}'.")

        if decision == ApprovalDecision.APPROVED:
            consent.status = ConsentStatus.ACTIVE.value
            consent.granted_at = _utc_now()
            consent.approved_by = actor.user_id
            action = AuditAction.CONSENT_APPROVED
        else:
            action = AuditAction.CONSENT_REJECTED

        record_decision(approval, decision, actor.user_id, notes)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=action,
            target_type="performer_consent",
            target_id=consent.id,
            details={"decision": decision.value},
        )
        self.db.commit()
        return consent

    def revoke(self, actor: ActorContext, project_id: str, performer_id: str, purpose: str, reason: str | None = None) -> PerformerConsentModel:
        """AT-CNS-004.1: revoking one purpose never touches any sibling consent row for
        the same performer -- each purpose is its own row (DEC-059), so there is nothing
        else to leave untouched."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "consent.manage", project)
        performer = self.performers.get_scoped(performer_id, actor.org_id)
        consent = self.consents.active_for_purpose(performer.id, purpose)
        if consent is None:
            raise InvalidStateError(f"No active consent for performer '{performer_id}', purpose '{purpose}'.")

        consent.status = ConsentStatus.REVOKED.value
        consent.revoked_at = _utc_now()
        consent.revoked_by = actor.user_id
        consent.revocation_reason = reason
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CONSENT_REVOKED,
            target_type="performer_consent",
            target_id=consent.id,
            details={"performer_id": performer.id, "purpose": purpose, "reason": reason},
        )
        self.db.commit()
        return consent

    def evaluate(self, performer_id: str, purpose: str, project_id: str | None = None) -> ConsentEvaluation:
        """A pure decision over active rows: ``allow`` or ``deny(reason)`` (architecture
        doc §6.2). Every gated action elsewhere in D4 calls this rather than querying
        ``performer_consents`` itself."""
        consent = self.consents.active_for_purpose(performer_id, purpose)
        if consent is None:
            return ConsentEvaluation(allowed=False, reason="no_active_consent")
        if consent.valid_until and consent.valid_until < _utc_now():
            return ConsentEvaluation(allowed=False, reason="expired")
        if consent.project_scope and project_id and project_id not in consent.project_scope:
            return ConsentEvaluation(allowed=False, reason="out_of_project_scope")
        return ConsentEvaluation(allowed=True)

    def require(self, performer_id: str, purpose: str, project_id: str | None = None) -> None:
        """Raise ConsentRequiredError unless ``evaluate`` allows this (purpose, performer)."""
        if not self.evaluate(performer_id, purpose, project_id).allowed:
            raise ConsentRequiredError(purpose)


class VoiceProfileService:
    """D4 (TFD-CNS-005): "permission to use recorded audio is not permission to clone" --
    a minimal structural record just to prove the ``voice_clone`` purpose is checked
    independently of ``reference_storage``. The full voice workflow (synthesis, dubbing,
    localisation) is FD-V2 and not built here."""

    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.voice_profiles = VoiceProfileRepository(db)
        self.consent = ConsentService(db)
        self.authz = AuthzService(db)
        self.audit = AuditRepository(db)

    def create_voice_profile(
        self,
        actor: ActorContext,
        project_id: str,
        *,
        kind: str,
        character_id: str | None = None,
        performer_id: str | None = None,
    ) -> VoiceProfileModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        if kind == "clone" and performer_id:
            self.consent.require(performer_id, "voice_clone", project_id)

        profile = self.voice_profiles.add(
            VoiceProfileModel(
                organization_id=project.organization_id,
                project_id=project.id,
                character_id=character_id,
                performer_id=performer_id,
                kind=kind,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.VOICE_PROFILE_CREATED,
            target_type="voice_profile",
            target_id=profile.id,
            details={"kind": kind},
        )
        self.db.commit()
        return profile

    def list_voice_profiles(self, actor: ActorContext, project_id: str) -> List[VoiceProfileModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.voice_profiles.list_for_project(project.id)
