"""API tests for Historical Research (Workflow G-02, Questions, Sources, Claims, Conflicts)."""

from tests.support import as_actor, create_project


def test_research_questions_crud(client, tenant):
    project = create_project(client, tenant, title="Kalinga Epic")
    headers = as_actor(tenant.user_id)

    # 1. Create Question
    create_resp = client.post(
        f"/api/v1/projects/{project['id']}/research/questions",
        json={"text": "What iron smelting techniques were used in 3rd c. BCE?", "category": "technology"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    q = create_resp.json()
    assert q["text"] == "What iron smelting techniques were used in 3rd c. BCE?"
    assert q["category"] == "technology"
    assert q["status"] == "open"
    assert q["project_version"] == 1

    # 2. List Questions
    list_resp = client.get(
        f"/api/v1/projects/{project['id']}/research/questions",
        headers=headers,
    )
    assert list_resp.status_code == 200
    questions = list_resp.json()
    assert len(questions) == 1
    assert questions[0]["id"] == q["id"]


def test_research_sources_crud(client, tenant):
    project = create_project(client, tenant, title="Kalinga Epic")
    headers = as_actor(tenant.user_id)

    # 1. Create Source
    create_resp = client.post(
        f"/api/v1/projects/{project['id']}/research/sources",
        json={
            "title": "Excavations at Sisupalgarh",
            "tier": "tier_1_primary",
            "author": "B.B. Lal",
            "publication_year": 1949,
            "locator": "Ancient India No. 5, pp. 62-105",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    s = create_resp.json()
    assert s["title"] == "Excavations at Sisupalgarh"
    assert s["tier"] == "tier_1_primary"
    assert s["author"] == "B.B. Lal"

    # 2. List Sources
    list_resp = client.get(
        f"/api/v1/projects/{project['id']}/research/sources",
        headers=headers,
    )
    assert list_resp.status_code == 200
    sources = list_resp.json()
    assert len(sources) == 1
    assert sources[0]["id"] == s["id"]


def test_historical_research_vertical_slice_e2e(client, tenant):
    project = create_project(client, tenant, title="Kalinga Campaign")
    headers = as_actor(tenant.user_id)

    # 1. Trigger Historical Research G-02 workflow
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/historical-research",
        json={"topic": "Kalinga Maurya warfare and fortifications", "sync_execution": True},
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
    claims = candidates["research_claims"]
    questions = candidates["research_questions"]
    assert len(claims) >= 2
    assert len(questions) >= 1
    assert any("tier_1_primary" in c["source_tier"] for c in claims)

    # 3. Approve research candidates
    approval_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "notes": "Verified by historical consultant",
            "approved_claim_ids": [c["id"] for c in claims],
            "approved_question_ids": [q["id"] for q in questions],
        },
        headers=headers,
    )
    assert approval_resp.status_code == 200
    assert approval_resp.json()["new_project_version"] == 2

    # 4. Verify canonical claims promoted
    claims_resp = client.get(f"/api/v1/projects/{project['id']}/research/claims", headers=headers)
    assert claims_resp.status_code == 200
    canonical_claims = claims_resp.json()
    assert len(canonical_claims) == len(claims)
    assert canonical_claims[0]["project_version"] == 2

    # 5. Verify canonical questions promoted
    q_resp = client.get(f"/api/v1/projects/{project['id']}/research/questions", headers=headers)
    assert q_resp.status_code == 200
    canonical_questions = q_resp.json()
    assert len(canonical_questions) == len(questions)

    # 6. Verify audit trail
    audit_resp = client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=headers)
    assert audit_resp.status_code == 200
    actions = [a["action"] for a in audit_resp.json()]
    assert "workflow_started" in actions
    assert "candidates_extracted" in actions
    assert "approval_decided" in actions
    assert "research_committed" in actions


def test_historical_research_rejection_leaves_state_untouched(client, tenant):
    project = create_project(client, tenant, title="Chola Naval Expedition")
    headers = as_actor(tenant.user_id)

    # Trigger G-02
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/historical-research",
        json={"topic": "Chola naval expeditions", "sync_execution": True},
        headers=headers,
    )
    approval_id = wf_resp.json()["approval_request_id"]

    # Reject
    reject_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "rejected", "notes": "Disputed era, re-run with later period"},
        headers=headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["new_project_version"] == 1

    # Canonical claims must be empty
    claims_resp = client.get(f"/api/v1/projects/{project['id']}/research/claims", headers=headers)
    assert claims_resp.json() == []

    # Audit log records rejection
    actions = [a["action"] for a in client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=headers).json()]
    assert "research_rejected" in actions

