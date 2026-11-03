"""Project lifecycle and read models for the project workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sqlalchemy.orm import Session

from packages.domain.enums import AuditAction, ProjectStatus
from packages.persistence.models import (
    ApprovalRequestModel,
    AuditEventModel,
    EntityCandidateModel,
    EntityModel,
    ProjectModel,
    ProjectVersionModel,
    SceneCandidateModel,
    SceneModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CandidateRepository,
    CanonicalRepository,
    ProjectRepository,
)
from packages.services.identity import ActorContext


@dataclass
class CandidateOverview:
    scenes: List[SceneCandidateModel]
    entities: List[EntityCandidateModel]
    approvals: List[ApprovalRequestModel]


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.audit = AuditRepository(db)

    def create(
        self,
        actor: ActorContext,
        *,
        title: str,
        logline: str | None = None,
        genre: str | None = None,
    ) -> ProjectModel:
        project = self.projects.add(
            ProjectModel(
                organization_id=actor.org_id,
                title=title,
                logline=logline,
                genre=genre,
                status=ProjectStatus.ACTIVE.value,
                current_version=1,
                created_by=actor.user_id,
            )
        )
        self.projects.add_version(
            ProjectVersionModel(
                project_id=project.id,
                version_number=1,
                branch_name="main",
                commit_message="Initial project baseline creation",
                committed_by=actor.user_id,
                snapshot_data={"title": title, "logline": logline, "genre": genre},
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=actor.org_id,
            actor_id=actor.user_id,
            action=AuditAction.PROJECT_CREATED,
            target_type="project",
            target_id=project.id,
            details={"title": title},
        )
        self.db.commit()
        self.db.refresh(project)
        return project

    def list(self, actor: ActorContext) -> List[ProjectModel]:
        return self.projects.list_for_org(actor.org_id)

    def get(self, actor: ActorContext, project_id: str) -> ProjectModel:
        return self.projects.get_scoped(project_id, actor.org_id)

    def versions(self, actor: ActorContext, project_id: str) -> List[ProjectVersionModel]:
        self.get(actor, project_id)
        return self.projects.list_versions(project_id)

    def audit_log(self, actor: ActorContext, project_id: str) -> List[AuditEventModel]:
        self.get(actor, project_id)
        return self.audit.list_for_project(project_id)

    def canonical_scenes(self, actor: ActorContext, project_id: str) -> List[SceneModel]:
        self.get(actor, project_id)
        return CanonicalRepository(self.db).scenes_for_project(project_id)

    def canonical_entities(self, actor: ActorContext, project_id: str) -> List[EntityModel]:
        self.get(actor, project_id)
        return CanonicalRepository(self.db).entities_for_project(project_id)

    def candidates(self, actor: ActorContext, project_id: str) -> CandidateOverview:
        self.get(actor, project_id)
        candidates = CandidateRepository(self.db)
        return CandidateOverview(
            scenes=candidates.scenes_for_project(project_id),
            entities=candidates.entities_for_project(project_id),
            approvals=ApprovalRepository(self.db).list_for_project(project_id),
        )
