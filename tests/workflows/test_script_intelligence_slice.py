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
from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    ApprovalRequestModel,
    AuditEventModel,
    EntityModel,
    ProjectModel,
    SceneModel,
)

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


def test_script_intelligence_vertical_slice_e2e():
    client = TestClient(app)

    # 1. Create a project
    create_resp = client.post(
        "/api/v1/projects",
        json={
            "title": "The Himalayan Chronicle",
            "logline": "An expedition unearths a lost celestial sanctuary.",
            "genre": "Mythological Adventure",
        },
    )
    assert create_resp.status_code == 201
    project_data = create_resp.json()
    project_id = project_data["id"]
    assert project_data["current_version"] == 1

    # 2. Upload script asset
    file_bytes = SAMPLE_SCREENPLAY.encode("utf-8")
    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/assets/upload",
        files={"file": ("himalayan_chronicle.fountain", io.BytesIO(file_bytes), "text/plain")},
    )
    assert upload_resp.status_code == 200
    asset_data = upload_resp.json()
    asset_id = asset_data["asset_id"]
    assert asset_data["checksum_sha256"]

    # 3. Trigger Script Intelligence workflow
    trigger_resp = client.post(
        f"/api/v1/projects/{project_id}/workflows/script-intelligence",
        json={"script_asset_id": asset_id, "sync_execution": True},
    )
    assert trigger_resp.status_code == 200
    workflow_data = trigger_resp.json()
    assert workflow_data["status"] == "awaiting_approval"
    approval_id = workflow_data["approval_request_id"]
    assert approval_id

    # 4. Inspect proposed candidates
    candidates_resp = client.get(f"/api/v1/projects/{project_id}/candidates")
    assert candidates_resp.status_code == 200
    c_data = candidates_resp.json()
    assert len(c_data["scenes"]) == 2
    assert len(c_data["entities"]) >= 2

    # 5. Submit human approval
    approval_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "actor_id": project_data.get("created_by") or "test-director",
            "notes": "Approved for production bible",
            "approved_scene_ids": [s["id"] for s in c_data["scenes"]],
            "approved_entity_ids": [e["id"] for e in c_data["entities"]],
        },
    )
    assert approval_resp.status_code == 200
    assert approval_resp.json()["new_project_version"] == 2

    # 6. Verify canonical scenes promoted to project state
    scenes_resp = client.get(f"/api/v1/projects/{project_id}/scenes")
    assert scenes_resp.status_code == 200
    scenes = scenes_resp.json()
    assert len(scenes) == 2
    assert scenes[0]["heading"] == "EXT. HIMALAYAN PASS - DAWN"
    assert scenes[0]["project_version"] == 2

    # 7. Verify canonical entities promoted
    entities_resp = client.get(f"/api/v1/projects/{project_id}/entities")
    assert entities_resp.status_code == 200
    entities = entities_resp.json()
    assert len(entities) >= 2
    entity_names = [e["name"] for e in entities]
    assert "Vikram" in entity_names or "Priya" in entity_names

    # 8. Verify audit log trail
    audit_resp = client.get(f"/api/v1/projects/{project_id}/audit-log")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    actions = [l["action"] for l in logs]
    assert "project_created" in actions
    assert "asset_uploaded" in actions
    assert "candidates_extracted" in actions
    assert "script_intelligence_committed" in actions
