"""End-to-End vertical slice test for Script Intelligence (PRD §6.1, Wireframe S-02/S-03).

Validates the full user journey:
1. Create project
2. Upload script asset to immutable storage
3. Trigger Script Intelligence LangGraph workflow
4. Verify candidates extracted and approval request pending
5. Submit human approval decision
6. Verify canonical project version increment, scenes/entities committed, and audit event emitted.
"""

import io

import pytest
from starlette.testclient import TestClient

from apps.api.main import app

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


@pytest.fixture
def client():
    return TestClient(app)


def _create_project_with_pending_approval(client, tenant):
    create_resp = client.post(
        "/api/v1/projects",
        json={
            "title": "The Himalayan Chronicle",
            "logline": "An expedition unearths a lost celestial sanctuary.",
            "genre": "Mythological Adventure",
            "organization_id": tenant.org_id,
            "actor_id": tenant.user_id,
        },
    )
    assert create_resp.status_code == 201
    project = create_resp.json()
    assert project["current_version"] == 1
    assert project["created_by"] == tenant.user_id

    upload_resp = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        files={"file": ("himalayan_chronicle.fountain", io.BytesIO(SAMPLE_SCREENPLAY.encode()), "text/plain")},
    )
    assert upload_resp.status_code == 200
    asset = upload_resp.json()
    assert asset["checksum_sha256"]

    trigger_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"script_asset_id": asset["asset_id"], "sync_execution": True},
    )
    assert trigger_resp.status_code == 200
    workflow = trigger_resp.json()
    assert workflow["status"] == "awaiting_approval"
    assert workflow["approval_request_id"]
    return project, workflow["approval_request_id"]


def test_script_intelligence_vertical_slice_e2e(client, tenant):
    project, approval_id = _create_project_with_pending_approval(client, tenant)
    project_id = project["id"]

    candidates_resp = client.get(f"/api/v1/projects/{project_id}/candidates")
    assert candidates_resp.status_code == 200
    c_data = candidates_resp.json()
    assert len(c_data["scenes"]) == 2
    assert len(c_data["entities"]) >= 2

    approval_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "actor_id": project["created_by"],
            "notes": "Approved for production bible",
            "approved_scene_ids": [s["id"] for s in c_data["scenes"]],
            "approved_entity_ids": [e["id"] for e in c_data["entities"]],
        },
    )
    assert approval_resp.status_code == 200
    assert approval_resp.json()["new_project_version"] == 2

    scenes = client.get(f"/api/v1/projects/{project_id}/scenes").json()
    assert len(scenes) == 2
    assert scenes[0]["heading"] == "EXT. HIMALAYAN PASS - DAWN"
    assert scenes[0]["project_version"] == 2

    entities = client.get(f"/api/v1/projects/{project_id}/entities").json()
    entity_names = [e["name"] for e in entities]
    assert "Vikram" in entity_names or "Priya" in entity_names

    actions = [log["action"] for log in client.get(f"/api/v1/projects/{project_id}/audit-log").json()]
    assert "project_created" in actions
    assert "asset_uploaded" in actions
    assert "candidates_extracted" in actions
    assert "script_intelligence_committed" in actions

    # A decided approval cannot be decided twice
    again = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "approved", "actor_id": project["created_by"]},
    )
    assert again.status_code == 409


def test_rejection_is_final_and_leaves_canonical_state_untouched(client, tenant):
    project, approval_id = _create_project_with_pending_approval(client, tenant)

    resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "rejected", "actor_id": project["created_by"], "notes": "Wrong draft"},
    )
    assert resp.status_code == 200
    assert resp.json()["new_project_version"] == 1

    approvals = client.get(f"/api/v1/projects/{project['id']}/candidates").json()["approvals"]
    assert [a["status"] for a in approvals] == ["decided"]
    assert client.get(f"/api/v1/projects/{project['id']}/scenes").json() == []


def test_decision_by_unknown_or_foreign_actor_is_refused(client, tenant, other_tenant):
    project, approval_id = _create_project_with_pending_approval(client, tenant)

    for actor in ("not-a-user", other_tenant.user_id):
        resp = client.post(
            f"/api/v1/approvals/{approval_id}/decide",
            json={"decision": "approved", "actor_id": actor},
        )
        assert resp.status_code == 403, actor

    approvals = client.get(f"/api/v1/projects/{project['id']}/candidates").json()["approvals"]
    assert approvals[0]["status"] == "pending"
