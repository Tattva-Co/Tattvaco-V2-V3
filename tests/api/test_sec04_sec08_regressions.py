"""Regression tests for docs/audit/08 SEC-04 (unvalidated cross-tenant foreign ids) and
SEC-08 (unknown approval scope silently routed to a fallback service)."""

from __future__ import annotations

from packages.persistence.database import SessionLocal
from packages.persistence.models import ApprovalRequestModel
from tests.support import as_actor, create_project, project_with_pending_approval, upload_script


def test_research_source_cannot_reference_another_tenants_asset(client, tenant, other_tenant):
    foreign_project = create_project(client, other_tenant, title="Foreign")
    foreign_upload = upload_script(client, other_tenant, foreign_project["id"])
    assert foreign_upload.status_code == 200, foreign_upload.text
    foreign_asset_id = foreign_upload.json()["asset_id"]

    project = create_project(client, tenant, title="Mine")
    resp = client.post(
        f"/api/v1/projects/{project['id']}/research/sources",
        json={"title": "A source", "asset_id": foreign_asset_id},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 404, resp.text


def test_research_source_accepts_an_asset_from_the_same_project(client, tenant):
    project = create_project(client, tenant, title="Mine")
    upload = upload_script(client, tenant, project["id"])
    assert upload.status_code == 200, upload.text

    resp = client.post(
        f"/api/v1/projects/{project['id']}/research/sources",
        json={"title": "A source", "asset_id": upload.json()["asset_id"]},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 200, resp.text


def test_unknown_approval_scope_is_rejected_not_routed_to_a_fallback_service(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)

    db = SessionLocal()
    try:
        approval = db.get(ApprovalRequestModel, workflow["approval_request_id"])
        approval.scope = "some_future_workflow_nobody_wrote_a_handler_for"
        db.commit()
    finally:
        db.close()

    resp = client.post(
        f"/api/v1/approvals/{workflow['approval_request_id']}/decide",
        json={"decision": "approved"},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 422, resp.text

    # Confirm it was NOT silently routed to ScriptIntelligenceService: the scene/entity
    # candidates from the original script-intelligence run must remain untouched.
    candidates = client.get(
        f"/api/v1/projects/{project['id']}/candidates", headers=as_actor(tenant.user_id)
    ).json()
    assert all(s["status"] == "proposed" for s in candidates["scenes"])
