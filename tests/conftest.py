"""Shared pytest fixtures.

Database-backed tests run against the local Postgres container (see docker-compose.yml).
Every fixture-created tenant is fully purged afterwards in foreign-key-safe order so
tests never leave rows behind in the development database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterator, List

import pytest

from packages.persistence.database import SessionLocal
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

SAMPLE_SCRIPT = """
EXT. RAJPUT FORTRESS - DAY

A fierce dust storm sweeps across the high ramparts.
RANA VEER (30s), clad in weathered armor, watches the distant valley.

RANA VEER
They arrive before dusk. Prepare the cavalry.

INT. WAR COUNCIL CHAMBER - NIGHT

Torches flicker against ancient stone walls.
BHAVANI (20s) unrolls a strategic parchment on the iron table.

BHAVANI
The northern pass is compromised. We hold the bridge.
"""


@dataclass
class Tenant:
    org_id: str
    user_id: str


def purge_organization(org_id: str) -> None:
    """Delete every row owned by an organization, children first."""
    db = SessionLocal()
    try:
        project_ids: List[str] = [
            pid for (pid,) in db.query(ProjectModel.id).filter_by(organization_id=org_id).all()
        ]
        run_ids: List[str] = [
            rid for (rid,) in db.query(WorkflowRunModel.id).filter_by(organization_id=org_id).all()
        ]
        if run_ids:
            db.query(OutboxTaskModel).filter(OutboxTaskModel.workflow_run_id.in_(run_ids)).delete(
                synchronize_session=False
            )
        if project_ids:
            for model in (
                AuditEventModel,
                ApprovalRequestModel,
                SceneCandidateModel,
                EntityCandidateModel,
                SceneModel,
                EntityModel,
                ProjectVersionModel,
            ):
                db.query(model).filter(model.project_id.in_(project_ids)).delete(
                    synchronize_session=False
                )
        db.query(WorkflowRunModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(AssetModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(ProjectModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(UserModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(OrganizationModel).filter_by(id=org_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def create_tenant(role: str = "director") -> Tenant:
    org_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(OrganizationModel(id=org_id, name="Test Studio", slug=f"test-{org_id[:8]}"))
        db.flush()
        db.add(
            UserModel(
                id=user_id,
                organization_id=org_id,
                email=f"{user_id[:8]}@test.example",
                full_name="Test Director",
                role=role,
            )
        )
        db.commit()
    finally:
        db.close()
    return Tenant(org_id=org_id, user_id=user_id)


@pytest.fixture
def tenant() -> Iterator[Tenant]:
    t = create_tenant()
    yield t
    purge_organization(t.org_id)


@pytest.fixture
def other_tenant() -> Iterator[Tenant]:
    t = create_tenant()
    yield t
    purge_organization(t.org_id)
