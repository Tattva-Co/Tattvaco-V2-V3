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
    FilmBibleRuleCandidateModel,
    ProjectMembershipModel,
    ProjectModel,
    ProjectVersionModel,
    ResearchClaimCandidateModel,
    ResearchQuestionCandidateModel,
    SceneCandidateModel,
    SceneModel,
    StoryboardPanelCandidateModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CandidateRepository,
    CanonicalRepository,
    ProjectMembershipRepository,
    ProjectRepository,
    RoleTemplateRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext


@dataclass
class CandidateOverview:
    scenes: List[SceneCandidateModel]
    entities: List[EntityCandidateModel]
    research_claims: List[ResearchClaimCandidateModel]
    research_questions: List[ResearchQuestionCandidateModel]
    storyboard_panels: List[StoryboardPanelCandidateModel]
    film_bible_rules: List[FilmBibleRuleCandidateModel]
    approvals: List[ApprovalRequestModel]


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.project_memberships = ProjectMembershipRepository(db)
        self.role_templates = RoleTemplateRepository(db)
        self.audit = AuditRepository(db)
        self.authz = AuthzService(db)

    def create(
        self,
        actor: ActorContext,
        *,
        title: str,
        logline: str | None = None,
        genre: str | None = None,
    ) -> ProjectModel:
        # project.create has no project to scope the check to yet; any active member of
        # the organization may create a project (ADR-003 §2).
        self.authz.require_org_member(actor)
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
        self.db.flush()
        # Grant the creator the project_owner role on their own new project. An org owner
        # wouldn't need this (AuthzService bypasses project_memberships for owners), but a
        # plain 'member' creating their first project otherwise couldn't act on it at all
        # -- there is no separate "invite yourself" step. 'project_owner' (not 'director')
        # specifically: JRN-01 (Guided Workspace section 1, which every project must pass
        # before anything else unlocks) is act_capability=project.admin throughout, which
        # 'director' does not grant -- a creator holding only 'director' could create a
        # project and then never be able to complete its own setup.
        owner_template = self.role_templates.get_by_key(actor.org_id, "project_owner")
        if owner_template is not None:
            self.project_memberships.add(
                ProjectMembershipModel(
                    user_id=actor.user_id, project_id=project.id, role_template_id=owner_template.id
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
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return project

    def versions(self, actor: ActorContext, project_id: str) -> List[ProjectVersionModel]:
        self.get(actor, project_id)
        return self.projects.list_versions(project_id)

    def audit_log(self, actor: ActorContext, project_id: str) -> List[AuditEventModel]:
        project = self.get(actor, project_id)
        self.authz.require(actor, "audit.read", project)
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
            research_claims=candidates.claims_for_project(project_id),
            research_questions=candidates.questions_for_project(project_id),
            storyboard_panels=candidates.storyboard_panels_for_project(project_id),
            film_bible_rules=candidates.film_bible_rules_for_project(project_id),
            approvals=ApprovalRepository(self.db).list_for_project(project_id),
        )
