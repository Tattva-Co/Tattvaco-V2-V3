"""Character identity, physical profile versioning, facial references and
scene-anchored character states (D4, TFD-CHR-001/002/005/006/007).

Not a LangGraph workflow -- like ScreenplayGovernanceService, this is director-authored
profile data with a draft/approve state machine, not AI-generated candidate content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from packages.domain.enums import ApprovalDecision, AuditAction, CharacterVersionStatus
from packages.domain.errors import InvalidStateError, ValidationFailure
from packages.persistence.models import (
    ApprovalRequestModel,
    CharacterFacialReferenceModel,
    CharacterModel,
    CharacterStateModel,
    CharacterVersionModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AssetRepository,
    AuditRepository,
    CanonicalRepository,
    CharacterFacialReferenceRepository,
    CharacterRepository,
    CharacterStateRepository,
    CharacterVersionRepository,
    ProjectRepository,
)
from packages.services.authz import AuthzService
from packages.services.consent import ConsentService
from packages.services.identity import ActorContext
from packages.services.script_review import record_decision

#: C8's generalized approval target (DEC-049's pattern): decided through
#: CharacterService.decide_version, never the generic POST /approvals/{id}/decide.
CHARACTER_VERSION_TARGET_TYPE = "character_version"
CHARACTER_VERSION_APPROVAL_SCOPE = "character_version_decision"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_characteristics(patch: Dict[str, Any]) -> None:
    """AT-CHR-005.1: every characteristic carries ``{source, status, confidence,
    approved_by, version}``; a save missing ``source`` is rejected, 422."""
    for field_name, envelope in patch.items():
        if not isinstance(envelope, dict) or not envelope.get("source"):
            raise ValidationFailure(f"Characteristic '{field_name}' is missing required 'source'.")


class CharacterService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.characters = CharacterRepository(db)
        self.versions = CharacterVersionRepository(db)
        self.facial_references = CharacterFacialReferenceRepository(db)
        self.states = CharacterStateRepository(db)
        self.approvals = ApprovalRepository(db)
        self.assets = AssetRepository(db)
        self.canonical = CanonicalRepository(db)
        self.authz = AuthzService(db)
        self.consent = ConsentService(db)
        self.audit = AuditRepository(db)

    # -- identity + physical profile versioning (TFD-CHR-001/005/006) ----------------

    def propose_version(
        self,
        actor: ActorContext,
        project_id: str,
        character_id: str,
        *,
        identity_patch: Dict[str, Any] | None = None,
        physical_patch: Dict[str, Any] | None = None,
    ) -> tuple[CharacterVersionModel, ApprovalRequestModel]:
        """AT-CHR-006.1: editing a field never touches the approved version -- it
        creates a new draft, copying every other field forward unedited."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        character = self.characters.get_scoped(character_id, project.id)
        _validate_characteristics(identity_patch or {})
        _validate_characteristics(physical_patch or {})

        current = (
            self.versions.get_scoped(character.current_version_id, project.id)
            if character.current_version_id
            else None
        )
        new_identity = {**(current.identity_profile if current else {}), **(identity_patch or {})}
        new_physical = {**(current.physical_profile if current else {}), **(physical_patch or {})}

        version = self.versions.add(
            CharacterVersionModel(
                character_id=character.id,
                project_id=project.id,
                organization_id=project.organization_id,
                version_number=self.versions.next_version_number(character.id),
                status=CharacterVersionStatus.DRAFT.value,
                parent_version_id=current.id if current else None,
                created_from="manual_edit",
                identity_profile=new_identity,
                physical_profile=new_physical,
                created_by=actor.user_id,
            )
        )
        approval = self.approvals.add(
            ApprovalRequestModel(
                target_type=CHARACTER_VERSION_TARGET_TYPE,
                target_id=version.id,
                project_id=project.id,
                organization_id=project.organization_id,
                scope=CHARACTER_VERSION_APPROVAL_SCOPE,
                candidate_summary={"character_id": character.id, "version_number": version.version_number},
            )
        )
        version.approval_request_id = approval.id
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CHARACTER_VERSION_DRAFTED,
            target_type="character_version",
            target_id=version.id,
            details={"character_id": character.id, "version_number": version.version_number},
        )
        self.db.commit()
        return version, approval

    def decide_version(
        self, actor: ActorContext, project_id: str, version_id: str, decision: ApprovalDecision, notes: str | None = None
    ) -> CharacterVersionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "approval.creative", project)
        version = self.versions.get_scoped(version_id, project.id)
        if version.status != CharacterVersionStatus.DRAFT.value:
            raise InvalidStateError(f"Character version '{version_id}' is not awaiting review.")
        approval = self.approvals.get_pending_for_target(CHARACTER_VERSION_TARGET_TYPE, version.id)
        if approval is None:
            raise InvalidStateError(f"No pending approval for character version '{version_id}'.")
        character = self.characters.get_scoped(version.character_id, project.id)

        if decision == ApprovalDecision.APPROVED:
            version.status = CharacterVersionStatus.APPROVED.value
            version.approved_by = actor.user_id
            version.approved_at = _utc_now()
            character.current_version_id = version.id
            action = AuditAction.CHARACTER_VERSION_APPROVED
        else:
            version.status = CharacterVersionStatus.REJECTED.value
            action = AuditAction.CHARACTER_VERSION_REJECTED

        record_decision(approval, decision, actor.user_id, notes)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=action,
            target_type="character_version",
            target_id=version.id,
            details={"decision": decision.value, "character_id": character.id},
        )
        self.db.commit()
        return version

    def get_detail(self, actor: ActorContext, project_id: str, character_id: str) -> tuple[CharacterModel, CharacterVersionModel | None]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        character = self.characters.get_scoped(character_id, project.id)
        current = self.versions.get_scoped(character.current_version_id, project.id) if character.current_version_id else None
        return character, current

    def list_versions(self, actor: ActorContext, project_id: str, character_id: str) -> List[CharacterVersionModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        self.characters.get_scoped(character_id, project.id)
        return self.versions.list_for_character(character_id)

    # -- facial identity references (TFD-CHR-002) -------------------------------------

    def add_facial_reference(
        self, actor: ActorContext, project_id: str, character_id: str, *, asset_id: str, role: str, facial_identity_version: int = 1
    ) -> CharacterFacialReferenceModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        character = self.characters.get_scoped(character_id, project.id)
        self.assets.get_for_project(asset_id, project.id)

        if character.performer_id:
            # AT-CHR-002.2: a character linked to performer P without active
            # reference_storage consent gets 403 consent_required: reference_storage.
            self.consent.require(character.performer_id, "reference_storage", project.id)

        reference = self.facial_references.add(
            CharacterFacialReferenceModel(
                character_id=character.id,
                organization_id=project.organization_id,
                asset_id=asset_id,
                role=role,
                facial_identity_version=facial_identity_version,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CHARACTER_FACIAL_REFERENCE_ADDED,
            target_type="character",
            target_id=character.id,
            details={"role": role, "asset_id": asset_id},
        )
        self.db.commit()
        return reference

    def list_facial_references(self, actor: ActorContext, project_id: str, character_id: str) -> List[CharacterFacialReferenceModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        self.characters.get_scoped(character_id, project.id)
        return self.facial_references.list_for_character(character_id)

    # -- character states over story time (TFD-CHR-007) -------------------------------

    def create_state(
        self,
        actor: ActorContext,
        project_id: str,
        character_id: str,
        *,
        state_label: str,
        applies_from_scene_id: str,
        applies_until_scene_id: str | None = None,
        deltas: Dict[str, Any] | None = None,
        evidence_refs: List[Dict[str, Any]] | None = None,
    ) -> CharacterStateModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        character = self.characters.get_scoped(character_id, project.id)
        scene_ids = {s.id for s in self.canonical.scenes_for_project(project.id)}
        if applies_from_scene_id not in scene_ids:
            raise ValidationFailure(f"Scene '{applies_from_scene_id}' is not in this project.")
        if applies_until_scene_id is not None and applies_until_scene_id not in scene_ids:
            raise ValidationFailure(f"Scene '{applies_until_scene_id}' is not in this project.")

        state = self.states.add(
            CharacterStateModel(
                character_id=character.id,
                project_id=project.id,
                organization_id=project.organization_id,
                state_label=state_label,
                applies_from_scene_id=applies_from_scene_id,
                applies_until_scene_id=applies_until_scene_id,
                deltas=deltas or {},
                evidence_refs=evidence_refs or [],
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CHARACTER_STATE_CREATED,
            target_type="character",
            target_id=character.id,
            details={"state_label": state_label},
        )
        self.db.commit()
        return state

    def list_states(self, actor: ActorContext, project_id: str, character_id: str) -> List[CharacterStateModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        self.characters.get_scoped(character_id, project.id)
        return self.states.list_for_character(character_id)

    def effective_state(self, actor: ActorContext, project_id: str, character_id: str, scene_number: int) -> CharacterStateModel | None:
        """AT-CHR-007.1: the latest state whose ``applies_from`` scene is at or before
        ``scene_number`` and whose ``applies_until`` (if any) has not yet been reached --
        resolved against scene *number* (shots don't exist until D7/D9, so there is no
        shot to anchor against yet; scenes are the finest grain available now)."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        self.characters.get_scoped(character_id, project.id)
        scenes_by_id = {s.id: s.scene_number for s in self.canonical.scenes_for_project(project.id)}

        candidates = []
        for state in self.states.list_for_character(character_id):
            from_number = scenes_by_id.get(state.applies_from_scene_id)
            if from_number is None or from_number > scene_number:
                continue
            until_number = scenes_by_id.get(state.applies_until_scene_id) if state.applies_until_scene_id else None
            if until_number is not None and until_number <= scene_number:
                continue
            candidates.append((from_number, state))

        if not candidates:
            return None
        return max(candidates, key=lambda pair: pair[0])[1]
