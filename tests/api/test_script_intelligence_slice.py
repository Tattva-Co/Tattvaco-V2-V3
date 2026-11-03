"""End-to-end vertical slice for Script Intelligence (PRD §6.1, Wireframe S-02/S-03).

Create project → upload script → run graph to the approval gate → review candidates →
decide → canonical version, scenes/entities and audit trail are updated.
"""

from tests.support import as_actor, project_with_pending_approval


def test_script_intelligence_vertical_slice_e2e(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    project_id, approval_id = project["id"], workflow["approval_request_id"]
    headers = as_actor(tenant.user_id)
    assert project["created_by"] == tenant.user_id
    assert workflow["candidate_summary"]["scene_count"] == 2

    c_data = client.get(f"/api/v1/projects/{project_id}/candidates", headers=headers).json()
    assert len(c_data["scenes"]) == 2
    assert len(c_data["entities"]) >= 2

    approval_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "notes": "Approved for production bible",
            "approved_scene_ids": [s["id"] for s in c_data["scenes"]],
            "approved_entity_ids": [e["id"] for e in c_data["entities"]],
        },
        headers=headers,
    )
    assert approval_resp.status_code == 200, approval_resp.text
    body = approval_resp.json()
    assert body["new_project_version"] == 2
    assert body["run_status"] == "completed"

    scenes = client.get(f"/api/v1/projects/{project_id}/scenes", headers=headers).json()
    assert [s["heading"] for s in scenes] == ["EXT. HIMALAYAN PASS - DAWN", "INT. MONASTERY ARCHIVE - NIGHT"]
    assert all(s["project_version"] == 2 for s in scenes)

    entity_names = {e["name"] for e in client.get(f"/api/v1/projects/{project_id}/entities", headers=headers).json()}
    assert {"Vikram", "Priya"} <= entity_names

    versions = client.get(f"/api/v1/projects/{project_id}/versions", headers=headers).json()
    assert [v["version_number"] for v in versions] == [2, 1]

    actions = [log["action"] for log in client.get(f"/api/v1/projects/{project_id}/audit-log", headers=headers).json()]
    for expected in (
        "project_created",
        "asset_uploaded",
        "workflow_started",
        "candidates_extracted",
        "approval_decided",
        "script_intelligence_committed",
    ):
        assert expected in actions

    run = client.get(f"/api/v1/workflow-runs/{workflow['workflow_run_id']}", headers=headers).json()
    assert run["status"] == "completed"
    assert run["output_refs"]["new_version"] == 2

    again = client.post(f"/api/v1/approvals/{approval_id}/decide", json={"decision": "approved"}, headers=headers)
    assert again.status_code == 409
    assert again.json()["error"] == "InvalidStateError"


def test_partial_selection_promotes_only_chosen_candidates(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    c_data = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    first_scene = c_data["scenes"][0]["id"]

    resp = client.post(
        f"/api/v1/approvals/{workflow['approval_request_id']}/decide",
        json={"decision": "approved", "approved_scene_ids": [first_scene], "approved_entity_ids": []},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    assert len(client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()) == 1
    # An explicitly empty list means "none", not "all".
    assert client.get(f"/api/v1/projects/{project['id']}/entities", headers=headers).json() == []


def test_rejection_is_final_and_leaves_canonical_state_untouched(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)

    resp = client.post(
        f"/api/v1/approvals/{workflow['approval_request_id']}/decide",
        json={"decision": "rejected", "notes": "Wrong draft"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["new_project_version"] == 1
    assert resp.json()["run_status"] == "rejected"

    c_data = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    assert [a["status"] for a in c_data["approvals"]] == ["decided"]
    assert [a["decision"] for a in c_data["approvals"]] == ["rejected"]
    assert {s["status"] for s in c_data["scenes"]} == {"rejected"}
    assert client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json() == []
