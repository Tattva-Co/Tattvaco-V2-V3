"""Costume Bible, costume states, and character x scene costume assignment (D5,
TFD-CST-001/002/003).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Sequence

from sqlalchemy.orm import Session

from packages.domain.enums import ApprovalDecision, AuditAction, WorldEntityVersionStatus
from packages.domain.errors import InvalidStateError, NotFoundError, ValidationFailure
from packages.persistence.models import (
    ApprovalRequestModel,
    ContinuityFindingModel,
    CostumeAssignmentModel,
    CostumeModel,
    CostumeStateModel,
    CostumeVersionModel,
    ResearchClaimModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CharacterRepository,
    ContinuityFindingRepository,
    CostumeAssignmentRepository,
    CostumeRepository,
    CostumeStateRepository,
    CostumeVersionRepository,
    ProjectRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext
from packages.services.script_review import record_decision

#: C8's generalized approval target (DEC-049/DEC-061's pattern): decided through
#: CostumeService.decide_version, never the generic POST /approvals/{id}/decide.
COSTUME_VERSION_TARGET_TYPE = "costume_version"
COSTUME_VERSION_APPROVAL_SCOPE = "costume_version_decision"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_characteristics(patch: Dict[str, Any]) -> None:
    """AT-CST-001.1's provenance requirement, same rule as D4/D5's other characteristic
    envelopes: a save missing `source` is rejected, 422."""
    for field_name, envelope in patch.items():
        if not isinstance(envelope, dict) or not envelope.get("source"):
            raise ValidationFailure(f"Characteristic '{field_name}' is missing required 'source'.")


class CostumeService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.costumes = CostumeRepository(db)
        self.versions = CostumeVersionRepository(db)
        self.states = CostumeStateRepository(db)
        self.assignments = CostumeAssignmentRepository(db)
        self.characters = CharacterRepository(db)
        self.approvals = ApprovalRepository(db)
        self.findings = ContinuityFindingRepository(db)
        self.authz = AuthzService(db)
        self.audit = AuditRepository(db)

    # -- costume identity ---------------------------------------------------------------

    def create_costume(self, actor: ActorContext, project_id: str, *, name: str, character_id: str | None = None) -> CostumeModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        if not name.strip():
            raise ValidationFailure("name is required.")
        if character_id is not None:
            self.characters.get_scoped(character_id, project.id)

        costume = self.costumes.add(
            CostumeModel(
                project_id=project.id,
                organization_id=project.organization_id,
                name=name.strip(),
                character_id=character_id,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.COSTUME_CREATED,
            target_type="costume",
            target_id=costume.id,
            details={"name": costume.name},
        )
        self.db.commit()
        return costume

    def list_costumes(self, actor: ActorContext, project_id: str) -> List[CostumeModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.costumes.list_for_project(project.id)

    def get_detail(self, actor: ActorContext, project_id: str, costume_id: str):
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        costume = self.costumes.get_scoped(costume_id, project.id)
        current = self.versions.get_scoped(costume.current_version_id, project.id) if costume.current_version_id else None
        return costume, current

    # -- costume profile versioning (TFD-CST-001) --------------------------------------

    def propose_version(
        self,
        actor: ActorContext,
        project_id: str,
        costume_id: str,
        *,
        profile_patch: Dict[str, Any] | None = None,
        claim_links: Sequence[str] | None = None,
    ) -> tuple[CostumeVersionModel, ApprovalRequestModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        costume = self.costumes.get_scoped(costume_id, project.id)
        _validate_characteristics(profile_patch or {})

        validated_claim_ids: List[str] = []
        for claim_id in claim_links or []:
            claim = self.db.get(ResearchClaimModel, claim_id)
            # AT-CST-001.1: "Claim links are by ID and tenant-checked" -- same 404-style
            # answer whether the claim is missing or belongs to another project.
            if claim is None or claim.project_id != project.id:
                raise NotFoundError(f"Research claim '{claim_id}' not found in this project.")
            validated_claim_ids.append(claim_id)

        current = self.versions.get_scoped(costume.current_version_id, project.id) if costume.current_version_id else None
        new_profile = {**(current.profile if current else {}), **(profile_patch or {})}
        new_claim_links = validated_claim_ids or (current.claim_links if current else [])

        version = self.versions.add(
            CostumeVersionModel(
                costume_id=costume.id,
                project_id=project.id,
                organization_id=project.organization_id,
                version_number=self.versions.next_version_number(costume.id),
                status=WorldEntityVersionStatus.DRAFT.value,
                parent_version_id=current.id if current else None,
                created_from="manual_edit",
                profile=new_profile,
                claim_links=new_claim_links,
                created_by=actor.user_id,
            )
        )
        approval = self.approvals.add(
            ApprovalRequestModel(
                target_type=COSTUME_VERSION_TARGET_TYPE,
                target_id=version.id,
                project_id=project.id,
                organization_id=project.organization_id,
                scope=COSTUME_VERSION_APPROVAL_SCOPE,
                candidate_summary={"costume_id": costume.id, "version_number": version.version_number},
            )
        )
        version.approval_request_id = approval.id
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.COSTUME_VERSION_DRAFTED,
            target_type="costume_version",
            target_id=version.id,
            details={"costume_id": costume.id, "version_number": version.version_number},
        )
        self.db.commit()
        return version, approval

    def decide_version(
        self, actor: ActorContext, project_id: str, version_id: str, decision: ApprovalDecision, notes: str | None = None
    ) -> CostumeVersionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "approval.creative", project)
        version = self.versions.get_scoped(version_id, project.id)
        if version.status != WorldEntityVersionStatus.DRAFT.value:
            raise InvalidStateError(f"Costume version '{version_id}' is not awaiting review.")
        approval = self.approvals.get_pending_for_target(COSTUME_VERSION_TARGET_TYPE, version.id)
        if approval is None:
            raise InvalidStateError(f"No pending approval for costume version '{version_id}'.")
        costume = self.costumes.get_scoped(version.costume_id, project.id)

        if decision == ApprovalDecision.APPROVED:
            version.status = WorldEntityVersionStatus.APPROVED.value
            version.approved_by = actor.user_id
            version.approved_at = _utc_now()
            costume.current_version_id = version.id
            action = AuditAction.COSTUME_VERSION_APPROVED
        else:
            version.status = WorldEntityVersionStatus.REJECTED.value
            action = AuditAction.COSTUME_VERSION_REJECTED

        record_decision(approval, decision, actor.user_id, notes)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=action,
            target_type="costume_version",
            target_id=version.id,
            details={"decision": decision.value, "costume_id": costume.id},
        )
        self.db.commit()
        return version

    def list_versions(self, actor: ActorContext, project_id: str, costume_id: str) -> List[CostumeVersionModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        self.costumes.get_scoped(costume_id, project.id)
        return self.versions.list_for_costume(costume_id)

    # -- costume states (TFD-CST-002) --------------------------------------------------

    def create_state(
        self, actor: ActorContext, project_id: str, costume_id: str, *, state_label: str, deltas: Dict[str, Any] | None = None
    ) -> CostumeStateModel:
        """Each call creates a new versioned row; approving one does not yet mark any
        shot package `stale` since neither `shots` nor `production_packages` exist
        (deferred to D7/D8/D9 -- see `CostumeStateModel`'s docstring)."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        costume = self.costumes.get_scoped(costume_id, project.id)
        existing = self.states.list_for_costume(costume.id)
        matching = [s for s in existing if s.state_label == state_label]
        previous = max(matching, key=lambda s: s.version) if matching else None

        state = self.states.add(
            CostumeStateModel(
                costume_id=costume.id,
                project_id=project.id,
                organization_id=project.organization_id,
                state_label=state_label,
                deltas=deltas or {},
                version=(previous.version + 1) if previous else 1,
                supersedes_id=previous.id if previous else None,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.COSTUME_STATE_CREATED,
            target_type="costume",
            target_id=costume.id,
            details={"state_label": state_label, "version": state.version},
        )
        self.db.commit()
        return state

    def list_states(self, actor: ActorContext, project_id: str, costume_id: str) -> List[CostumeStateModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        self.costumes.get_scoped(costume_id, project.id)
        return self.states.list_for_costume(costume_id)

    # -- costume assignment (TFD-CST-003) ----------------------------------------------

    def assign(
        self,
        actor: ActorContext,
        project_id: str,
        *,
        character_id: str,
        scene_id: str,
        costume_id: str,
        costume_state_id: str | None = None,
    ) -> CostumeAssignmentModel:
        """AT-CST-003.1: a second costume assigned to the same (character, scene, state)
        is still recorded, not silently resolved -- it raises a continuity finding."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        self.characters.get_scoped(character_id, project.id)
        self.costumes.get_scoped(costume_id, project.id)
        if costume_state_id is not None:
            self.states.get_scoped(costume_state_id, project.id)

        conflict = self.assignments.find_conflicting(character_id, scene_id, costume_state_id)
        assignment = self.assignments.add(
            CostumeAssignmentModel(
                project_id=project.id,
                organization_id=project.organization_id,
                character_id=character_id,
                scene_id=scene_id,
                costume_id=costume_id,
                costume_state_id=costume_state_id,
                created_by=actor.user_id,
            )
        )
        if conflict is not None and conflict.costume_id != costume_id:
            self.findings.add(
                ContinuityFindingModel(
                    project_id=project.id,
                    organization_id=project.organization_id,
                    finding_type="costume_conflict",
                    scene_id=scene_id,
                    details={
                        "character_id": character_id,
                        "existing_costume_id": conflict.costume_id,
                        "new_costume_id": costume_id,
                        "costume_state_id": costume_state_id,
                    },
                )
            )
            self.audit.record(
                project_id=project.id,
                organization_id=project.organization_id,
                actor_id=actor.user_id,
                action=AuditAction.CONTINUITY_FINDING_RAISED,
                target_type="scene",
                target_id=scene_id,
                details={"finding_type": "costume_conflict", "character_id": character_id},
            )

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.COSTUME_ASSIGNMENT_CREATED,
            target_type="scene",
            target_id=scene_id,
            details={"character_id": character_id, "costume_id": costume_id},
        )
        self.db.commit()
        return assignment

    def list_continuity_findings(self, actor: ActorContext, project_id: str) -> List[ContinuityFindingModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.findings.list_for_project(project.id)
