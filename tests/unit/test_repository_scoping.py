"""Regression tests for SEC-04 (docs/audit/08): id-only lookups must not cross tenants.

get_question_scoped/get_source_scoped/get_rule_scoped have no caller anywhere in the
application yet -- these are the "safe by construction" replacements for the previous
get_question/get_source/get_rule, which took only an id and could read any tenant's row.
Tested directly at the repository layer since no route exposes them (yet).
"""

from __future__ import annotations

from packages.domain.errors import NotFoundError
from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    FilmBibleRuleModel,
    ProjectModel,
    ResearchQuestionModel,
    ResearchSourceModel,
)
from packages.persistence.repositories import FilmBibleRepository, ResearchRepository
from tests.support import create_tenant, purge_organization


def test_question_source_and_rule_lookups_are_scoped_to_their_project():
    owner = create_tenant()
    intruder = create_tenant()
    db = SessionLocal()
    try:
        project = ProjectModel(organization_id=owner.org_id, title="Owned Project", created_by=owner.user_id)
        other_project = ProjectModel(
            organization_id=intruder.org_id, title="Someone Else's Project", created_by=intruder.user_id
        )
        db.add_all([project, other_project])
        db.flush()

        question = ResearchQuestionModel(
            project_id=project.id, organization_id=owner.org_id, project_version=1, text="Q?", status="open"
        )
        source = ResearchSourceModel(
            project_id=project.id, organization_id=owner.org_id, project_version=1, title="S", tier="tier_1_primary"
        )
        rule = FilmBibleRuleModel(
            project_id=project.id,
            organization_id=owner.org_id,
            project_version=1,
            category="color_palette",
            title="R",
            rule_text="text",
            strictness="guideline",
        )
        db.add_all([question, source, rule])
        db.commit()

        research = ResearchRepository(db)
        film_bible = FilmBibleRepository(db)

        # Correct project: found.
        assert research.get_question_scoped(question.id, project.id).id == question.id
        assert research.get_source_scoped(source.id, project.id).id == source.id
        assert film_bible.get_rule_scoped(rule.id, project.id).id == rule.id

        # Wrong project: the id is real, but scoping to a different project must 404,
        # exactly as if the row didn't exist (no existence oracle).
        try:
            research.get_question_scoped(question.id, other_project.id)
            assert False, "expected NotFoundError"
        except NotFoundError:
            pass
        try:
            research.get_source_scoped(source.id, other_project.id)
            assert False, "expected NotFoundError"
        except NotFoundError:
            pass
        try:
            film_bible.get_rule_scoped(rule.id, other_project.id)
            assert False, "expected NotFoundError"
        except NotFoundError:
            pass
    finally:
        db.close()
        purge_organization(owner.org_id)
        purge_organization(intruder.org_id)
