"""API tests for Film Bible & Visual World Rules (Workflow G-04, Rules, Approvals)."""

from tests.support import as_actor, create_project


def test_film_bible_rules_crud(client, tenant):
    project = create_project(client, tenant, title="Kalinga Visual Bible")
    headers = as_actor(tenant.user_id)

    # 1. Create a manual visual rule
    create_resp = client.post(
        f"/api/v1/projects/{project['id']}/film-bible/rules",
        json={
            "category": "color_palette",
            "title": "Terracotta and Ochre Palette",
            "rule_text": "Strict reliance on natural terracotta and yellow ochre pigments.",
            "negative_prompt_guidance": "neon, synthetic dyes",
            "strictness": "mandatory",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    rule = create_resp.json()
    assert rule["category"] == "color_palette"
    assert rule["title"] == "Terracotta and Ochre Palette"
    assert rule["strictness"] == "mandatory"
    assert rule["project_version"] == 1

    # 2. List rules
    list_resp = client.get(
        f"/api/v1/projects/{project['id']}/film-bible/rules",
        headers=headers,
    )
    assert list_resp.status_code == 200
    rules = list_resp.json()
    assert len(rules) == 1
    assert rules[0]["id"] == rule["id"]

    # 3. Filter by category
    filter_resp = client.get(
        f"/api/v1/projects/{project['id']}/film-bible/rules?category=color_palette",
        headers=headers,
    )
    assert len(filter_resp.json()) == 1

    empty_filter_resp = client.get(
        f"/api/v1/projects/{project['id']}/film-bible/rules?category=camera_language",
        headers=headers,
    )
    assert len(empty_filter_resp.json()) == 0


def test_film_bible_synthesis_vertical_slice_e2e(client, tenant):
    project = create_project(client, tenant, title="Mauryan Architecture")
    headers = as_actor(tenant.user_id)

    # 1. Trigger Film Bible Synthesis G-04 workflow
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/film-bible-synthesis",
        json={"user_notes": "Authentic ancient Indian visual language with natural materials", "sync_execution": True},
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
    rules = candidates["film_bible_rules"]
    assert len(rules) >= 6  # All 6 core categories generated
    categories = {r["category"] for r in rules}
    assert "tone_aesthetic" in categories
    assert "color_palette" in categories
    assert "lighting_atmosphere" in categories
    assert "architectural_environment" in categories
    assert "material_culture" in categories
    assert "camera_language" in categories

    # 3. Approve all synthesized visual rules
    rule_ids = [r["id"] for r in rules]
    approval_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "notes": "Approved by Art Director",
            "approved_rule_ids": rule_ids,
        },
        headers=headers,
    )
    assert approval_resp.status_code == 200
    assert approval_resp.json()["new_project_version"] == 2

    # 4. Verify canonical rules committed
    canonical_resp = client.get(f"/api/v1/projects/{project['id']}/film-bible/rules", headers=headers)
    assert canonical_resp.status_code == 200
    canonical_rules = canonical_resp.json()
    assert len(canonical_rules) == len(rules)
    assert canonical_rules[0]["project_version"] == 2

    # 5. Verify audit log
    audit_resp = client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=headers)
    assert audit_resp.status_code == 200
    actions = [a["action"] for a in audit_resp.json()]
    assert "workflow_started" in actions
    assert "candidates_extracted" in actions
    assert "approval_decided" in actions
    assert "film_bible_committed" in actions


def test_film_bible_conflict_detection(client, tenant):
    project = create_project(client, tenant, title="Conflict Detection Test")
    headers = as_actor(tenant.user_id)

    # 1. Trigger G-04 with modern/conflicting notes containing 'neon' and 'synthetic'
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/film-bible-synthesis",
        json={"user_notes": "Decorated with bright neon illumination and plastic materials", "sync_execution": True},
        headers=headers,
    )
    assert wf_resp.status_code == 200

    # 2. Inspect candidates and verify conflict warning
    c_resp = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers)
    rules = c_resp.json()["film_bible_rules"]
    conflicted = [r for r in rules if r.get("conflict_warning") is not None]
    assert len(conflicted) >= 1
    assert "Anachronism" in conflicted[0]["conflict_warning"]


def test_film_bible_partial_approval(client, tenant):
    project = create_project(client, tenant, title="Partial Film Bible")
    headers = as_actor(tenant.user_id)

    # 1. Trigger G-04
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/film-bible-synthesis",
        json={"sync_execution": True},
        headers=headers,
    )
    approval_id = wf_resp.json()["approval_request_id"]

    # 2. Candidates
    c_resp = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers)
    rules = c_resp.json()["film_bible_rules"]

    # 3. Approve only the first rule
    selected = [rules[0]["id"]]
    approval_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "notes": "Tone rule only",
            "approved_rule_ids": selected,
        },
        headers=headers,
    )
    assert approval_resp.status_code == 200
    assert approval_resp.json()["new_project_version"] == 2

    # 4. Canonical rules count is 1
    canonical = client.get(f"/api/v1/projects/{project['id']}/film-bible/rules", headers=headers).json()
    assert len(canonical) == 1
    assert canonical[0]["title"] == rules[0]["title"]


def test_film_bible_rejection(client, tenant):
    project = create_project(client, tenant, title="Rejected Bible")
    headers = as_actor(tenant.user_id)

    # 1. Trigger G-04
    wf_resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/film-bible-synthesis",
        json={"sync_execution": True},
        headers=headers,
    )
    approval_id = wf_resp.json()["approval_request_id"]

    # 2. Reject
    reject_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "rejected", "notes": "Need deeper grounding in Sisupalgarh excavations"},
        headers=headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["new_project_version"] == 1

    # 3. Canonical rules must be empty
    canonical = client.get(f"/api/v1/projects/{project['id']}/film-bible/rules", headers=headers).json()
    assert canonical == []

    # 4. Audit log records rejection
    actions = [a["action"] for a in client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=headers).json()]
    assert "film_bible_rejected" in actions

