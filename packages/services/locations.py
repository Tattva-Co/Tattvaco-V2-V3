"""Location/environment profile versioning, the legacy location link, and scene-level
environment states (D5, TFD-ENV-001/002/004).

Not a LangGraph workflow -- like CharacterService, this is director-authored profile
data with a draft/approve state machine, not AI-generated candidate content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from packages.domain.enums import ApprovalDecision, AuditAction, WorldEntityVersionStatus
from packages.domain.errors import InvalidStateError, ValidationFailure
from packages.persistence.models import ApprovalRequestModel, EnvironmentStateModel, LocationVersionModel
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CanonicalRepository,
    EnvironmentStateRepository,
    LocationRepository,
    LocationVersionRepository,
    ProjectRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext
from packages.services.script_review import record_decision

#: C8's generalized approval target (DEC-049/DEC-061's pattern): decided through
#: LocationService.decide_version, never the generic POST /approvals/{id}/decide.
LOCATION_VERSION_TARGET_TYPE = "location_version"
LOCATION_VERSION_APPROVAL_SCOPE = "location_version_decision"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_characteristics(patch: Dict[str, Any]) -> None:
    """AT-ENV-001.1 ("stored with provenance"), the same envelope rule as D4's
    AT-CHR-005.1: every characteristic needs a `source`, 422 otherwise."""
    for field_name, envelope in patch.items():
        if not isinstance(envelope, dict) or not envelope.get("source"):
            raise ValidationFailure(f"Characteristic '{field_name}' is missing required 'source'.")


class LocationService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.locations = LocationRepository(db)
        self.versions = LocationVersionRepository(db)
        self.environment_states = EnvironmentStateRepository(db)
        self.approvals = ApprovalRepository(db)
        self.canonical = CanonicalRepository(db)
        self.authz = AuthzService(db)
        self.audit = AuditRepository(db)

    # -- environment profile versioning (TFD-ENV-001) --------------------------------

    def propose_version(
        self, actor: ActorContext, project_id: str, location_id: str, *, profile_patch: Dict[str, Any] | None = None
    ) -> tuple[LocationVersionModel, ApprovalRequestModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        location = self.locations.get_scoped(location_id, project.id)
        _validate_characteristics(profile_patch or {})

        current = self.versions.get_scoped(location.current_version_id, project.id) if location.current_version_id else None
        new_profile = {**(current.profile if current else {}), **(profile_patch or {})}

        version = self.versions.add(
            LocationVersionModel(
                location_id=location.id,
                project_id=project.id,
                organization_id=project.organization_id,
                version_number=self.versions.next_version_number(location.id),
                status=WorldEntityVersionStatus.DRAFT.value,
                parent_version_id=current.id if current else None,
                created_from="manual_edit",
                profile=new_profile,
                created_by=actor.user_id,
            )
        )
        approval = self.approvals.add(
            ApprovalRequestModel(
                target_type=LOCATION_VERSION_TARGET_TYPE,
                target_id=version.id,
                project_id=project.id,
                organization_id=project.organization_id,
                scope=LOCATION_VERSION_APPROVAL_SCOPE,
                candidate_summary={"location_id": location.id, "version_number": version.version_number},
            )
        )
        version.approval_request_id = approval.id
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.LOCATION_VERSION_DRAFTED,
            target_type="location_version",
            target_id=version.id,
            details={"location_id": location.id, "version_number": version.version_number},
        )
        self.db.commit()
        return version, approval

    def decide_version(
        self, actor: ActorContext, project_id: str, version_id: str, decision: ApprovalDecision, notes: str | None = None
    ) -> LocationVersionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "approval.creative", project)
        version = self.versions.get_scoped(version_id, project.id)
        if version.status != WorldEntityVersionStatus.DRAFT.value:
            raise InvalidStateError(f"Location version '{version_id}' is not awaiting review.")
        approval = self.approvals.get_pending_for_target(LOCATION_VERSION_TARGET_TYPE, version.id)
        if approval is None:
            raise InvalidStateError(f"No pending approval for location version '{version_id}'.")
        location = self.locations.get_scoped(version.location_id, project.id)

        if decision == ApprovalDecision.APPROVED:
            version.status = WorldEntityVersionStatus.APPROVED.value
            version.approved_by = actor.user_id
            version.approved_at = _utc_now()
            location.current_version_id = version.id
            action = AuditAction.LOCATION_VERSION_APPROVED
        else:
            version.status = WorldEntityVersionStatus.REJECTED.value
            action = AuditAction.LOCATION_VERSION_REJECTED

        record_decision(approval, decision, actor.user_id, notes)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=action,
            target_type="location_version",
            target_id=version.id,
            details={"decision": decision.value, "location_id": location.id},
        )
        self.db.commit()
        return version

    def get_detail(self, actor: ActorContext, project_id: str, location_id: str):
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        location = self.locations.get_scoped(location_id, project.id)
        current = self.versions.get_scoped(location.current_version_id, project.id) if location.current_version_id else None
        return location, current

    def list_versions(self, actor: ActorContext, project_id: str, location_id: str) -> List[LocationVersionModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        self.locations.get_scoped(location_id, project.id)
        return self.versions.list_for_location(location_id)

    # -- legacy location link (TFD-ENV-004) -------------------------------------------

    def adopt_legacy_location(self, actor: ActorContext, project_id: str, location_id: str) -> List[str]:
        """Link every scene whose `location_name` exactly matches this location's
        `canonical_name` -- `scenes.location_name` itself is never touched (AT-ENV-004.1)."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        location = self.locations.get_scoped(location_id, project.id)

        matched_scene_ids: List[str] = []
        for scene in self.canonical.scenes_for_project(project.id):
            if scene.location_name == location.canonical_name:
                scene.location_id = location.id
                matched_scene_ids.append(scene.id)

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.LOCATION_ADOPTED,
            target_type="location",
            target_id=location.id,
            details={"matched_scene_ids": matched_scene_ids},
        )
        self.db.commit()
        return matched_scene_ids

    # -- environment states (TFD-ENV-002) ---------------------------------------------

    def create_environment_state(
        self, actor: ActorContext, project_id: str, scene_id: str, *, changes: Dict[str, Any], location_id: str | None = None
    ) -> EnvironmentStateModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        scene_ids = {s.id for s in self.canonical.scenes_for_project(project.id)}
        if scene_id not in scene_ids:
            raise ValidationFailure(f"Scene '{scene_id}' is not in this project.")

        previous = self.environment_states.current_for_scene(scene_id)
        if previous is not None:
            previous.status = "superseded"

        state = self.environment_states.add(
            EnvironmentStateModel(
                project_id=project.id,
                organization_id=project.organization_id,
                scene_id=scene_id,
                location_id=location_id,
                changes=changes,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.ENVIRONMENT_STATE_CREATED,
            target_type="scene",
            target_id=scene_id,
            details={"changes": changes},
        )
        self.db.commit()
        return state

    def get_effective_environment_state(self, actor: ActorContext, project_id: str, scene_id: str) -> EnvironmentStateModel | None:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.environment_states.current_for_scene(scene_id)
