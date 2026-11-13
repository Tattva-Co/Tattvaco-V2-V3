"""Cinematography Bible (camera/lens/lighting libraries, composition rules, virtual
camera profile, visual language profile) and AI shot-planning recommendations with
override (D6, TFD-CIN-004/005).

Not a LangGraph workflow for the Bible itself -- like CostumeService/LocationService,
this is director-authored profile data with a draft/approve state machine. The
recommendation generator IS a ModelGateway capability (consistent with every other
deterministic generator in this codebase), but a recommendation is request/response, not
a multi-step graph with an approval gate -- "no field is ever auto-applied" (AT-CIN-004.1)
already means there's nothing to approve into canon here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Sequence

from sqlalchemy.orm import Session

from packages.ai.gateway import get_model_gateway
from packages.core.config import get_settings
from packages.domain.enums import ApprovalDecision, AuditAction, WorldEntityVersionStatus
from packages.domain.errors import InvalidStateError, NotFoundError, ValidationFailure
from packages.persistence.models import (
    ApprovalRequestModel,
    CameraProfileModel,
    CinematographyProfileVersionModel,
    CinematographyRecommendationModel,
    LensProfileModel,
    LightingProfileModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CameraProfileRepository,
    CinematographyProfileVersionRepository,
    CinematographyRecommendationRepository,
    LensProfileRepository,
    LightingProfileRepository,
    ProjectRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext
from packages.services.script_review import record_decision

#: C8's generalized approval target (DEC-049/061/064's pattern): decided through
#: CinematographyService.decide_version, never the generic POST /approvals/{id}/decide.
CINEMATOGRAPHY_VERSION_TARGET_TYPE = "cinematography_profile_version"
CINEMATOGRAPHY_VERSION_APPROVAL_SCOPE = "cinematography_version_decision"

_VALID_CAMERA_SPEC_KINDS = {"physical", "virtual"}


def _utc_now() -> datetime:
    return datetime.now(UTC)


class CinematographyService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.camera_profiles = CameraProfileRepository(db)
        self.lens_profiles = LensProfileRepository(db)
        self.lighting_profiles = LightingProfileRepository(db)
        self.versions = CinematographyProfileVersionRepository(db)
        self.recommendations = CinematographyRecommendationRepository(db)
        self.approvals = ApprovalRepository(db)
        self.authz = AuthzService(db)
        self.audit = AuditRepository(db)

    # -- camera/lens/lighting libraries (TFD-CIN-005) ----------------------------------

    def create_camera_profile(
        self, actor: ActorContext, project_id: str, *, name: str, spec_kind: str, specs: Dict[str, Any] | None = None
    ) -> CameraProfileModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        if spec_kind not in _VALID_CAMERA_SPEC_KINDS:
            raise ValidationFailure(f"Invalid spec_kind '{spec_kind}'; must be one of {sorted(_VALID_CAMERA_SPEC_KINDS)}.")
        if not name.strip():
            raise ValidationFailure("name is required.")

        profile = self.camera_profiles.add(
            CameraProfileModel(
                project_id=project.id,
                organization_id=project.organization_id,
                name=name.strip(),
                spec_kind=spec_kind,
                specs=specs or {},
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CAMERA_PROFILE_CREATED,
            target_type="camera_profile",
            target_id=profile.id,
            details={"name": profile.name, "spec_kind": spec_kind},
        )
        self.db.commit()
        return profile

    def list_camera_profiles(self, actor: ActorContext, project_id: str) -> List[CameraProfileModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.camera_profiles.list_for_project(project.id)

    def create_lens_profile(self, actor: ActorContext, project_id: str, *, name: str, specs: Dict[str, Any] | None = None) -> LensProfileModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        if not name.strip():
            raise ValidationFailure("name is required.")
        profile = self.lens_profiles.add(
            LensProfileModel(project_id=project.id, organization_id=project.organization_id, name=name.strip(), specs=specs or {}, created_by=actor.user_id)
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.LENS_PROFILE_CREATED,
            target_type="lens_profile",
            target_id=profile.id,
            details={"name": profile.name},
        )
        self.db.commit()
        return profile

    def list_lens_profiles(self, actor: ActorContext, project_id: str) -> List[LensProfileModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.lens_profiles.list_for_project(project.id)

    def create_lighting_profile(
        self, actor: ActorContext, project_id: str, *, name: str, specs: Dict[str, Any] | None = None
    ) -> LightingProfileModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        if not name.strip():
            raise ValidationFailure("name is required.")
        profile = self.lighting_profiles.add(
            LightingProfileModel(project_id=project.id, organization_id=project.organization_id, name=name.strip(), specs=specs or {}, created_by=actor.user_id)
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.LIGHTING_PROFILE_CREATED,
            target_type="lighting_profile",
            target_id=profile.id,
            details={"name": profile.name},
        )
        self.db.commit()
        return profile

    def list_lighting_profiles(self, actor: ActorContext, project_id: str) -> List[LightingProfileModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.lighting_profiles.list_for_project(project.id)

    # -- Cinematography Bible versioning (TFD-CIN-005) ---------------------------------

    def propose_bible_version(
        self,
        actor: ActorContext,
        project_id: str,
        *,
        camera_profile_ids: Sequence[str] = (),
        lens_profile_ids: Sequence[str] = (),
        lighting_profile_ids: Sequence[str] = (),
        composition_rules: Dict[str, Any] | None = None,
        virtual_camera_profile: Dict[str, Any] | None = None,
        visual_language: Dict[str, Any] | None = None,
    ) -> tuple[CinematographyProfileVersionModel, ApprovalRequestModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)

        for camera_id in camera_profile_ids:
            camera = self.db.get(CameraProfileModel, camera_id)
            if camera is None or camera.project_id != project.id:
                raise NotFoundError(f"Camera profile '{camera_id}' not found in this project.")
        for lens_id in lens_profile_ids:
            lens = self.db.get(LensProfileModel, lens_id)
            if lens is None or lens.project_id != project.id:
                raise NotFoundError(f"Lens profile '{lens_id}' not found in this project.")
        for lighting_id in lighting_profile_ids:
            lighting = self.db.get(LightingProfileModel, lighting_id)
            if lighting is None or lighting.project_id != project.id:
                raise NotFoundError(f"Lighting profile '{lighting_id}' not found in this project.")

        current = self.versions.get_current(project.id)
        version = self.versions.add(
            CinematographyProfileVersionModel(
                project_id=project.id,
                organization_id=project.organization_id,
                version_number=self.versions.next_version_number(project.id),
                status=WorldEntityVersionStatus.DRAFT.value,
                parent_version_id=current.id if current else None,
                camera_profile_ids=list(camera_profile_ids),
                lens_profile_ids=list(lens_profile_ids),
                lighting_profile_ids=list(lighting_profile_ids),
                composition_rules=composition_rules or {},
                virtual_camera_profile=virtual_camera_profile or {},
                visual_language=visual_language or {},
                created_by=actor.user_id,
            )
        )
        approval = self.approvals.add(
            ApprovalRequestModel(
                target_type=CINEMATOGRAPHY_VERSION_TARGET_TYPE,
                target_id=version.id,
                project_id=project.id,
                organization_id=project.organization_id,
                scope=CINEMATOGRAPHY_VERSION_APPROVAL_SCOPE,
                candidate_summary={"version_number": version.version_number},
            )
        )
        version.approval_request_id = approval.id
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CINEMATOGRAPHY_VERSION_DRAFTED,
            target_type="cinematography_profile_version",
            target_id=version.id,
            details={"version_number": version.version_number},
        )
        self.db.commit()
        return version, approval

    def decide_version(
        self, actor: ActorContext, project_id: str, version_id: str, decision: ApprovalDecision, notes: str | None = None
    ) -> CinematographyProfileVersionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "approval.creative", project)
        version = self.versions.get_scoped(version_id, project.id)
        if version.status != WorldEntityVersionStatus.DRAFT.value:
            raise InvalidStateError(f"Cinematography profile version '{version_id}' is not awaiting review.")
        approval = self.approvals.get_pending_for_target(CINEMATOGRAPHY_VERSION_TARGET_TYPE, version.id)
        if approval is None:
            raise InvalidStateError(f"No pending approval for cinematography profile version '{version_id}'.")

        if decision == ApprovalDecision.APPROVED:
            # AT-CIN-005.1: approving one version doesn't retroactively change an
            # earlier approved version's own status -- "current" is just whichever
            # approved row has the highest version_number (CinematographyProfileVersionRepository.get_current).
            version.status = WorldEntityVersionStatus.APPROVED.value
            version.approved_by = actor.user_id
            version.approved_at = _utc_now()
            action = AuditAction.CINEMATOGRAPHY_VERSION_APPROVED
        else:
            version.status = WorldEntityVersionStatus.REJECTED.value
            action = AuditAction.CINEMATOGRAPHY_VERSION_REJECTED

        record_decision(approval, decision, actor.user_id, notes)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=action,
            target_type="cinematography_profile_version",
            target_id=version.id,
            details={"decision": decision.value},
        )
        self.db.commit()
        return version

    def get_current_bible(self, actor: ActorContext, project_id: str) -> CinematographyProfileVersionModel | None:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.versions.get_current(project.id)

    def list_versions(self, actor: ActorContext, project_id: str) -> List[CinematographyProfileVersionModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.versions.list_for_project(project.id)

    # -- AI recommendations with override (TFD-CIN-004) --------------------------------

    def request_recommendation(self, actor: ActorContext, project_id: str, intent: str) -> CinematographyRecommendationModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "workflow.run", project)
        if not intent.strip():
            raise ValidationFailure("intent is required.")

        gateway = get_model_gateway(get_settings())
        result = gateway.recommend_cinematography(intent.strip())
        recommendation = self.recommendations.add(
            CinematographyRecommendationModel(
                project_id=project.id,
                organization_id=project.organization_id,
                intent_text=intent.strip(),
                recommendation=result.model_dump(),
                overrides={},
                generator_mode=gateway.mode,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CINEMATOGRAPHY_RECOMMENDATION_REQUESTED,
            target_type="cinematography_recommendation",
            target_id=recommendation.id,
            details={"intent": intent.strip()},
        )
        self.db.commit()
        return recommendation

    def override_recommendation(
        self, actor: ActorContext, project_id: str, recommendation_id: str, *, field_name: str, value: Any
    ) -> CinematographyRecommendationModel:
        """AT-CIN-004.2: the override is stored with the user, and the original
        recommendation is retained -- `recommendation` itself is never mutated."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        recommendation = self.recommendations.get_scoped(recommendation_id, project.id)
        if field_name not in recommendation.recommendation:
            raise ValidationFailure(f"'{field_name}' is not a recommended field.")

        overrides = dict(recommendation.overrides)
        overrides[field_name] = {"value": value, "overridden_by": actor.user_id, "overridden_at": _utc_now().isoformat()}
        recommendation.overrides = overrides

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.CINEMATOGRAPHY_RECOMMENDATION_OVERRIDDEN,
            target_type="cinematography_recommendation",
            target_id=recommendation.id,
            details={"field_name": field_name},
        )
        self.db.commit()
        return recommendation

    def list_recommendations(self, actor: ActorContext, project_id: str) -> List[CinematographyRecommendationModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.recommendations.list_for_project(project.id)
