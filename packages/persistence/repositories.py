"""SQLAlchemy repositories — the only layer that issues SQL.

Conventions:
- Repositories ``add``/``flush``/query but never ``commit``. The calling service owns the
  transaction (one commit per use case), so multi-row changes stay atomic.
- Lookups that must be tenant-scoped take an ``org_id`` and raise ``NotFoundError`` when the
  object is missing *or* belongs to another organization (no existence oracle).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, Iterable, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.enums import ApprovalStatus, AuditAction, OutboxStatus
from packages.domain.errors import NotFoundError
from packages.persistence.models import (
    ApprovalRequestModel,
    AssetModel,
    AuditEventModel,
    EntityCandidateModel,
    EntityModel,
    OrganizationModel,
    OutboxTaskModel,
    ProjectModel,
    ProjectVersionModel,
    SceneCandidateModel,
    SceneModel,
    UserModel,
    WorkflowRunModel,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class _Repository:
    def __init__(self, db: Session):
        self.db = db

    def _add(self, obj):
        self.db.add(obj)
        self.db.flush()  # assign primary keys so callers can reference them immediately
        return obj


class UserRepository(_Repository):
    DEFAULT_ORG_SLUG = "default-studio"

    def get(self, user_id: str) -> UserModel | None:
        return self.db.get(UserModel, user_id)

    def get_or_create_default_actor(self) -> UserModel:
        """Development bootstrap identity: the default studio org and its first user."""
        org = self.db.scalars(
            select(OrganizationModel).where(OrganizationModel.slug == self.DEFAULT_ORG_SLUG)
        ).first() or self.db.scalars(select(OrganizationModel)).first()
        if org is None:
            org = self._add(OrganizationModel(name="Default Studio Org", slug=self.DEFAULT_ORG_SLUG))

        user = self.db.scalars(
            select(UserModel).where(UserModel.organization_id == org.id).order_by(UserModel.created_at)
        ).first()
        if user is None:
            user = self._add(
                UserModel(
                    organization_id=org.id,
                    email="director@tattvaco.com",
                    full_name="Lead Film Director",
                    role="director",
                )
            )
        return user


class ProjectRepository(_Repository):
    def add(self, project: ProjectModel) -> ProjectModel:
        return self._add(project)

    def get_scoped(self, project_id: str, org_id: str, *, for_update: bool = False) -> ProjectModel:
        stmt = select(ProjectModel).where(
            ProjectModel.id == project_id, ProjectModel.organization_id == org_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        project = self.db.scalars(stmt).first()
        if project is None:
            raise NotFoundError(f"Project '{project_id}' not found.")
        return project

    def list_for_org(self, org_id: str) -> List[ProjectModel]:
        stmt = (
            select(ProjectModel)
            .where(ProjectModel.organization_id == org_id)
            .order_by(ProjectModel.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def add_version(self, version: ProjectVersionModel) -> ProjectVersionModel:
        return self._add(version)

    def list_versions(self, project_id: str) -> List[ProjectVersionModel]:
        stmt = (
            select(ProjectVersionModel)
            .where(ProjectVersionModel.project_id == project_id)
            .order_by(ProjectVersionModel.version_number.desc())
        )
        return list(self.db.scalars(stmt))


class AssetRepository(_Repository):
    def add(self, asset: AssetModel) -> AssetModel:
        return self._add(asset)

    def get_for_project(self, asset_id: str, project_id: str) -> AssetModel:
        stmt = select(AssetModel).where(AssetModel.id == asset_id, AssetModel.project_id == project_id)
        asset = self.db.scalars(stmt).first()
        if asset is None:
            raise NotFoundError(f"Asset '{asset_id}' not found in project.")
        return asset

    def get(self, asset_id: str) -> AssetModel | None:
        return self.db.get(AssetModel, asset_id)

    def list_for_project(self, project_id: str) -> List[AssetModel]:
        stmt = (
            select(AssetModel)
            .where(AssetModel.project_id == project_id)
            .order_by(AssetModel.created_at.desc())
        )
        return list(self.db.scalars(stmt))


class WorkflowRunRepository(_Repository):
    def add(self, run: WorkflowRunModel) -> WorkflowRunModel:
        return self._add(run)

    def get(self, run_id: str) -> WorkflowRunModel | None:
        return self.db.get(WorkflowRunModel, run_id)

    def get_scoped(self, run_id: str, org_id: str) -> WorkflowRunModel:
        run = self.get(run_id)
        if run is None or run.organization_id != org_id:
            raise NotFoundError(f"Workflow run '{run_id}' not found.")
        return run

    def set_status(
        self,
        run_id: str,
        status: str,
        *,
        output_refs: Dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        run = self.get(run_id)
        if run is None:
            return
        run.status = status
        if output_refs is not None:
            run.output_refs = output_refs
        if error_message is not None:
            run.error_message = error_message
        run.updated_at = utc_now()


class OutboxRepository(_Repository):
    def enqueue(self, workflow_run_id: str, task_type: str, payload: Dict[str, Any]) -> OutboxTaskModel:
        return self._add(
            OutboxTaskModel(
                workflow_run_id=workflow_run_id,
                task_type=task_type,
                payload=payload,
                status=OutboxStatus.PENDING.value,
            )
        )

    def claim_next(self, worker_id: str) -> OutboxTaskModel | None:
        """Atomically claim the oldest pending task (``FOR UPDATE SKIP LOCKED``)."""
        stmt = (
            select(OutboxTaskModel)
            .where(OutboxTaskModel.status == OutboxStatus.PENDING.value)
            .order_by(OutboxTaskModel.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        task = self.db.scalars(stmt).first()
        if task is None:
            return None
        task.status = OutboxStatus.CLAIMED.value
        task.claimed_by = worker_id
        task.claimed_at = utc_now()
        task.attempts += 1
        return task


class ApprovalRepository(_Repository):
    def add(self, approval: ApprovalRequestModel) -> ApprovalRequestModel:
        return self._add(approval)

    def get_scoped(self, approval_id: str, org_id: str, *, for_update: bool = False) -> ApprovalRequestModel:
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.id == approval_id, ApprovalRequestModel.organization_id == org_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        approval = self.db.scalars(stmt).first()
        if approval is None:
            raise NotFoundError(f"Approval request '{approval_id}' not found.")
        return approval

    def get_pending_for_run(self, run_id: str) -> ApprovalRequestModel | None:
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.workflow_run_id == run_id,
            ApprovalRequestModel.status == ApprovalStatus.PENDING.value,
        )
        return self.db.scalars(stmt).first()

    def list_for_project(self, project_id: str) -> List[ApprovalRequestModel]:
        stmt = (
            select(ApprovalRequestModel)
            .where(ApprovalRequestModel.project_id == project_id)
            .order_by(ApprovalRequestModel.created_at.desc())
        )
        return list(self.db.scalars(stmt))


class CandidateRepository(_Repository):
    def add_scene(self, candidate: SceneCandidateModel) -> SceneCandidateModel:
        return self._add(candidate)

    def add_entity(self, candidate: EntityCandidateModel) -> EntityCandidateModel:
        return self._add(candidate)

    def scenes_for_run(self, run_id: str) -> List[SceneCandidateModel]:
        stmt = (
            select(SceneCandidateModel)
            .where(SceneCandidateModel.workflow_run_id == run_id)
            .order_by(SceneCandidateModel.scene_number)
        )
        return list(self.db.scalars(stmt))

    def entities_for_run(self, run_id: str) -> List[EntityCandidateModel]:
        stmt = (
            select(EntityCandidateModel)
            .where(EntityCandidateModel.workflow_run_id == run_id)
            .order_by(EntityCandidateModel.category, EntityCandidateModel.name)
        )
        return list(self.db.scalars(stmt))

    def scenes_for_project(self, project_id: str) -> List[SceneCandidateModel]:
        stmt = (
            select(SceneCandidateModel)
            .where(SceneCandidateModel.project_id == project_id)
            .order_by(SceneCandidateModel.created_at, SceneCandidateModel.scene_number)
        )
        return list(self.db.scalars(stmt))

    def entities_for_project(self, project_id: str) -> List[EntityCandidateModel]:
        stmt = (
            select(EntityCandidateModel)
            .where(EntityCandidateModel.project_id == project_id)
            .order_by(EntityCandidateModel.category, EntityCandidateModel.name)
        )
        return list(self.db.scalars(stmt))


class CanonicalRepository(_Repository):
    def add_scenes(self, scenes: Iterable[SceneModel]) -> None:
        self.db.add_all(list(scenes))

    def add_entities(self, entities: Iterable[EntityModel]) -> None:
        self.db.add_all(list(entities))

    def scenes_for_project(self, project_id: str) -> List[SceneModel]:
        stmt = select(SceneModel).where(SceneModel.project_id == project_id).order_by(SceneModel.scene_number)
        return list(self.db.scalars(stmt))

    def entities_for_project(self, project_id: str) -> List[EntityModel]:
        stmt = (
            select(EntityModel)
            .where(EntityModel.project_id == project_id)
            .order_by(EntityModel.category, EntityModel.name)
        )
        return list(self.db.scalars(stmt))


class AuditRepository(_Repository):
    def record(
        self,
        *,
        project_id: str,
        organization_id: str,
        actor_id: str,
        action: AuditAction,
        target_type: str,
        target_id: str,
        details: Dict[str, Any] | None = None,
    ) -> AuditEventModel:
        return self._add(
            AuditEventModel(
                project_id=project_id,
                organization_id=organization_id,
                actor_id=actor_id,
                action=action.value,
                target_type=target_type,
                target_id=target_id,
                details=details or {},
            )
        )

    def list_for_project(self, project_id: str) -> List[AuditEventModel]:
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.project_id == project_id)
            .order_by(AuditEventModel.created_at.desc())
        )
        return list(self.db.scalars(stmt))
