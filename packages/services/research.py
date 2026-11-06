"""Canonical Historical Research service for questions, sources, claims, and conflicts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from packages.domain.enums import AuditAction
from packages.persistence.models import (
    ResearchClaimModel,
    ResearchConflictModel,
    ResearchQuestionModel,
    ResearchSourceModel,
)
from packages.persistence.repositories import (
    AssetRepository,
    AuditRepository,
    ProjectRepository,
    ResearchRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext


class ResearchService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.research = ResearchRepository(db)
        self.assets = AssetRepository(db)
        self.audit = AuditRepository(db)
        self.authz = AuthzService(db)

    def list_questions(self, actor: ActorContext, project_id: str, status: str | None = None) -> list[ResearchQuestionModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.research.list_questions(project_id, status=status)

    def create_question(
        self,
        actor: ActorContext,
        project_id: str,
        text: str,
        category: str = "general",
    ) -> ResearchQuestionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        question = ResearchQuestionModel(
            project_id=project.id,
            organization_id=project.organization_id,
            project_version=project.current_version,
            text=text,
            category=category,
            status="open",
        )
        self.research.add_question(question)
        self.db.flush()

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.RESEARCH_QUESTION_CREATED,
            target_type="research_question",
            target_id=question.id,
            details={"text": text, "category": category},
        )
        self.db.commit()
        return question

    def list_sources(self, actor: ActorContext, project_id: str) -> list[ResearchSourceModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.research.list_sources(project_id)

    def create_source(
        self,
        actor: ActorContext,
        project_id: str,
        title: str,
        tier: str = "tier_2_scholarly",
        author: str | None = None,
        publication_year: int | None = None,
        locator: str | None = None,
        url: str | None = None,
        asset_id: str | None = None,
        reliability_notes: str | None = None,
    ) -> ResearchSourceModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        if asset_id is not None:
            # Raises NotFoundError (404) if the asset doesn't exist or belongs to a
            # different project, preventing a source from pointing at another tenant's
            # asset (SEC-04, docs/audit/08).
            self.assets.get_for_project(asset_id, project.id)
        source = ResearchSourceModel(
            project_id=project.id,
            organization_id=project.organization_id,
            project_version=project.current_version,
            title=title,
            tier=tier,
            author=author,
            publication_year=publication_year,
            locator=locator,
            url=url,
            asset_id=asset_id,
            reliability_notes=reliability_notes,
        )
        self.research.add_source(source)
        self.db.flush()

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.RESEARCH_SOURCE_RECORDED,
            target_type="research_source",
            target_id=source.id,
            details={"title": title, "tier": tier, "author": author},
        )
        self.db.commit()
        return source

    def list_claims(
        self,
        actor: ActorContext,
        project_id: str,
        claim_class: str | None = None,
    ) -> list[ResearchClaimModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.research.list_claims(project_id, claim_class=claim_class)

    def list_conflicts(self, actor: ActorContext, project_id: str) -> list[ResearchConflictModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.research.list_conflicts(project_id)

