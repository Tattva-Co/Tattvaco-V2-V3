"""API tests for Storyboard Intelligence (Workflow G-03, Panels, Approvals)."""

from tests.support import as_actor, create_project


def test_storyboard_panels_empty_initially(client, tenant):
    project = create_project(client, tenant, title="Epic Battle")
    headers = as_actor(tenant.user_id)

    resp = client.get(
        f"/api/v1/projects/{project['id']}/storyboard/panels",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_storyboard_intelligence_vertical_slice_e2e(client, tenant):
    project = create_project(client, tenant, title="Dharma Yuddha")
    headers = as_actor(tenant.user_id)

    # 1. Trigger Storyboard Intelligence G-03 workflow
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/storyboard-intelligence",
        json={"brief": "Dramatic dusk battle sequence on the ramparts", "sync_execution": True},
        headers=headers,
    )
    assert wf_resp.status_code == 200
    wf = wf_resp.json()
    assert wf["status"] == "awaiting_approval"
    approval_id = wf["approval_request_id"]
    assert approval_id is not None

    # 2. Inspect candidates tray
    c_resp = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers)
    assert c_resp.status_code == 200
    candidates = c_resp.json()
    panels = candidates["storyboard_panels"]
    assert len(panels) >= 2
    assert all(p["status"] == "proposed" for p in panels)
    assert any(p["shot_type"] == "establishing" for p in panels)

    # 3. Approve storyboard panel candidates
    panel_ids = [p["id"] for p in panels]
    approval_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "notes": "Framing and lens choices approved by Director",
            "approved_panel_ids": panel_ids,
        },
        headers=headers,
    )
    assert approval_resp.status_code == 200
    assert approval_resp.json()["new_project_version"] == 2

    # 4. Verify canonical storyboard panels promoted
    panels_resp = client.get(f"/api/v1/projects/{project['id']}/storyboard/panels", headers=headers)
    assert panels_resp.status_code == 200
    canonical_panels = panels_resp.json()
    assert len(canonical_panels) == len(panels)
    assert canonical_panels[0]["project_version"] == 2
    assert canonical_panels[0]["panel_number"] == 1

    # 5. Verify audit trail
    audit_resp = client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=headers)
    assert audit_resp.status_code == 200
    actions = [a["action"] for a in audit_resp.json()]
    assert "workflow_started" in actions
    assert "candidates_extracted" in actions
    assert "approval_decided" in actions
    assert "storyboard_committed" in actions


def test_storyboard_intelligence_partial_approval(client, tenant):
    project = create_project(client, tenant, title="Chariot Siege")
    headers = as_actor(tenant.user_id)

    # 1. Trigger G-03
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/storyboard-intelligence",
        json={"brief": "Chariot charge sequences", "sync_execution": True},
        headers=headers,
    )
    approval_id = wf_resp.json()["approval_request_id"]

    # 2. Get candidates
    c_resp = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers)
    panels = c_resp.json()["storyboard_panels"]
    assert len(panels) >= 2

    # 3. Approve only the first panel
    selected = [panels[0]["id"]]
    approval_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "notes": "Approved panel 1 only",
            "approved_panel_ids": selected,
        },
        headers=headers,
    )
    assert approval_resp.status_code == 200
    assert approval_resp.json()["new_project_version"] == 2

    # 4. Check canonical panels - only 1 promoted
    panels_resp = client.get(f"/api/v1/projects/{project['id']}/storyboard/panels", headers=headers)
    canonical = panels_resp.json()
    assert len(canonical) == 1
    assert canonical[0]["panel_number"] == panels[0]["panel_number"]
    assert canonical[0]["description"] == panels[0]["description"]


def test_storyboard_intelligence_rejection(client, tenant):
    project = create_project(client, tenant, title="Night Ambush")
    headers = as_actor(tenant.user_id)

    # 1. Trigger G-03
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/storyboard-intelligence",
        json={"brief": "Night ambush", "sync_execution": True},
        headers=headers,
    )
    approval_id = wf_resp.json()["approval_request_id"]

    # 2. Reject
    reject_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "rejected", "notes": "Need more handheld close-ups"},
        headers=headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["new_project_version"] == 1

    # 3. Canonical panels must be empty
    panels_resp = client.get(f"/api/v1/projects/{project['id']}/storyboard/panels", headers=headers)
    assert panels_resp.json() == []

    # 4. Audit log records rejection
    actions = [a["action"] for a in client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=headers).json()]
    assert "storyboard_rejected" in actions
