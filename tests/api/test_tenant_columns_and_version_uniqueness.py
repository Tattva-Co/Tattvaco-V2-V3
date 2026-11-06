"""Regression tests for the C4/C5 leftovers (TFD-IAM-009, TFD-VER-001).

1. scenes, entities, scene/entity candidates and project_versions carry the owning
   project's organization_id on every row the application writes.
2. project_versions rejects a second row with the same (project_id, version_number).
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    EntityCandidateModel,
    EntityModel,
    ProjectVersionModel,
    SceneCandidateModel,
    SceneModel,
)
from tests.support import as_actor, create_project, project_with_pending_approval


def test_every_written_row_carries_the_project_organization(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    decided = client.post(
        f"/api/v1/approvals/{workflow['approval_request_id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decided.status_code == 200, decided.text

    db = SessionLocal()
    try:
        for model in (SceneCandidateModel, EntityCandidateModel, SceneModel, EntityModel, ProjectVersionModel):
            rows = db.query(model).filter_by(project_id=project["id"]).all()
            assert rows, f"no {model.__tablename__} rows written"
            assert {r.organization_id for r in rows} == {tenant.org_id}, model.__tablename__
    finally:
        db.close()


def test_duplicate_project_version_number_is_rejected_by_the_database(client, tenant):
    project = create_project(client, tenant)
    db = SessionLocal()
    try:
        db.add(
            ProjectVersionModel(
                project_id=project["id"],
                organization_id=tenant.org_id,
                version_number=1,  # create_project already wrote version 1
                branch_name="main",
                commit_message="duplicate on purpose",
                committed_by=tenant.user_id,
                snapshot_data={},
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()
