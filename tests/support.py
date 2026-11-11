"""Shared test helpers (plain functions/constants; fixtures live in conftest.py)."""


from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from typing import List

from sqlalchemy import text

from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    ApprovalRequestModel,
    AssetDerivativeModel,
    AssetModel,
    AuditEventModel,
    EntityCandidateModel,
    EntityModel,
    FilmBibleRuleCandidateModel,
    FilmBibleRuleModel,
    IdempotencyKeyModel,
    JourneyItemStateModel,
    JourneySectionEventModel,
    JourneyStalenessModel,
    MembershipModel,
    OrganizationModel,
    OutboxTaskModel,
    ProjectMembershipModel,
    ProjectModel,
    ProjectVersionModel,
    ResearchClaimCandidateModel,
    ResearchClaimModel,
    ResearchConflictModel,
    ResearchQuestionCandidateModel,
    ResearchQuestionModel,
    ResearchSourceModel,
    RoleTemplateCapabilityModel,
    RoleTemplateModel,
    SceneCandidateModel,
    SceneModel,
    StoryboardPanelCandidateModel,
    StoryboardPanelModel,
    UserModel,
    WorkflowRunModel,
)
from packages.persistence.repositories import RoleTemplateRepository

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
        # audit_events is append-only (C8: a BEFORE UPDATE OR DELETE trigger raises
        # unconditionally otherwise) -- this is the one legitimate, deliberate exception,
        # scoped (SET LOCAL) to just this transaction so no other code path gets it.
        db.execute(text("SET LOCAL tattva.allow_audit_mutation = 'true'"))
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
                # Film-bible rows reference research_claims, so they go first.
                FilmBibleRuleModel,
                FilmBibleRuleCandidateModel,
                AuditEventModel,
                ApprovalRequestModel,
                AssetDerivativeModel,
                ResearchConflictModel,
                ResearchClaimModel,
                ResearchQuestionModel,
                ResearchSourceModel,
                ResearchClaimCandidateModel,
                ResearchQuestionCandidateModel,
                StoryboardPanelCandidateModel,
                StoryboardPanelModel,
                SceneCandidateModel,
                EntityCandidateModel,
                SceneModel,
                EntityModel,
                ProjectVersionModel,
                ProjectMembershipModel,
                JourneyItemStateModel,
                JourneySectionEventModel,
                JourneyStalenessModel,
            ):
                db.query(model).filter(model.project_id.in_(project_ids)).delete(
                    synchronize_session=False
                )
        role_template_ids: List[str] = [
            rid for (rid,) in db.query(RoleTemplateModel.id).filter_by(organization_id=org_id).all()
        ]
        if role_template_ids:
            db.query(RoleTemplateCapabilityModel).filter(
                RoleTemplateCapabilityModel.role_template_id.in_(role_template_ids)
            ).delete(synchronize_session=False)
        db.query(IdempotencyKeyModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(MembershipModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(RoleTemplateModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(WorkflowRunModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(AssetModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(ProjectModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(UserModel).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(OrganizationModel).filter_by(id=org_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def create_tenant(role: str = "director") -> Tenant:
    """A brand-new org with one user, who is that org's owner (ADR-003 §2): every test
    tenant is alone in its own org, so this is the only mapping that preserves "a test
    tenant can do anything in its own org", which every existing test already assumes."""
    org_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(OrganizationModel(id=org_id, name="Test Studio", slug=f"test-{org_id[:8]}"))
        db.flush()
        RoleTemplateRepository(db).seed_defaults_for_org(org_id)
        db.add(
            UserModel(
                id=user_id,
                organization_id=org_id,
                email=f"{user_id[:8]}@test.example",
                full_name="Test Director",
                role=role,
            )
        )
        db.flush()
        db.add(MembershipModel(user_id=user_id, organization_id=org_id, org_role="owner", status="active"))
        db.commit()
    finally:
        db.close()
    return Tenant(org_id=org_id, user_id=user_id)


SAMPLE_SCREENPLAY = """
EXT. HIMALAYAN PASS - DAWN

Icy wind howls across the jagged mountain peaks.
VIKRAM (40s), a weathered cartographer, adjusts his brass telescope.

VIKRAM
The celestial alignment matches the scripture.

INT. MONASTERY ARCHIVE - NIGHT

Ancient scrolls line the floor-to-ceiling carved cedar shelves.
PRIYA (30s) illuminates a centuries-old mandala with an oil lamp.

PRIYA
The coordinates point to the sunken temple beneath the lake.
"""


def as_actor(user_id: str) -> dict:
    return {"X-Actor-ID": user_id}


def create_project(client, tenant, title="The Himalayan Chronicle") -> dict:
    resp = client.post(
        "/api/v1/projects",
        json={"title": title, "logline": "An expedition.", "genre": "Mythological Adventure"},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def upload_script(client, tenant, project_id, content: str = SAMPLE_SCREENPLAY, filename="chronicle.fountain", mime="text/plain"):
    return client.post(
        f"/api/v1/projects/{project_id}/assets/upload",
        files={"file": (filename, io.BytesIO(content.encode()), mime)},
        headers=as_actor(tenant.user_id),
    )


def project_with_pending_approval(client, tenant):
    project = create_project(client, tenant)
    upload = upload_script(client, tenant, project["id"])
    assert upload.status_code == 200, upload.text
    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"script_asset_id": upload.json()["asset_id"], "sync_execution": True},
        headers=as_actor(tenant.user_id),
    )
    assert trigger.status_code == 200, trigger.text
    workflow = trigger.json()
    assert workflow["status"] == "awaiting_approval"
    assert workflow["approval_request_id"]
    return project, workflow
