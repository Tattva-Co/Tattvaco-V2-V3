"""D3 (Story Intelligence v2): verbatim dialogue segments, character/location
resolution with legacy entity links, and non-uppercase (forced) cues end to end through
the real API. Acceptance criteria cited are docs/product/ACCEPTANCE_CRITERIA.md §3.6.
"""

from __future__ import annotations

from tests.support import as_actor, project_with_pending_approval


def _approve_everything(client, headers, project_id, approval_id, candidates):
    return client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "approved_scene_ids": [s["id"] for s in candidates["scenes"]],
            "approved_entity_ids": [e["id"] for e in candidates["entities"]],
        },
        headers=headers,
    )


# -- TFD-STY-002: verbatim dialogue segments -----------------------------------


def test_dialogue_segments_are_extracted_verbatim_and_linked_to_their_scene(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    assert workflow["candidate_summary"]["dialogue_segment_count"] == 2

    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    approved = _approve_everything(client, headers, project["id"], workflow["approval_request_id"], candidates)
    assert approved.status_code == 200, approved.text

    scenes = client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()
    scene_by_heading = {s["heading"]: s for s in scenes}
    dialogue = client.get(f"/api/v1/projects/{project['id']}/dialogue-segments", headers=headers).json()
    assert len(dialogue) == 2

    vikram_line = next(d for d in dialogue if d["character_name"] == "Vikram")
    assert vikram_line["line_text"] == "The celestial alignment matches the scripture."
    assert vikram_line["scene_id"] == scene_by_heading["EXT. HIMALAYAN PASS - DAWN"]["id"]
    assert vikram_line["project_version"] == 2

    priya_line = next(d for d in dialogue if d["character_name"] == "Priya")
    assert priya_line["line_text"] == "The coordinates point to the sunken temple beneath the lake."
    assert priya_line["scene_id"] == scene_by_heading["INT. MONASTERY ARCHIVE - NIGHT"]["id"]


def test_no_api_route_exists_to_mutate_a_canonical_dialogue_segment(client, tenant):
    """AT-STY-002.2: a canonical dialogue segment is never mutated by any API."""
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    _approve_everything(client, headers, project["id"], workflow["approval_request_id"], candidates)

    dialogue = client.get(f"/api/v1/projects/{project['id']}/dialogue-segments", headers=headers).json()
    segment_id = dialogue[0]["id"]

    for method in ("patch", "put", "delete"):
        resp = getattr(client, method)(
            f"/api/v1/projects/{project['id']}/dialogue-segments/{segment_id}",
            headers=headers,
            **({"json": {"line_text": "tampered"}} if method != "delete" else {}),
        )
        assert resp.status_code == 404, f"{method} unexpectedly routed to something: {resp.text}"


def test_a_rejected_scenes_dialogue_is_not_promoted(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    scene_candidates = candidates["scenes"]
    himalayan_scene = next(s for s in scene_candidates if "HIMALAYAN" in s["heading"])

    approved = client.post(
        f"/api/v1/approvals/{workflow['approval_request_id']}/decide",
        json={
            "decision": "approved",
            "approved_scene_ids": [himalayan_scene["id"]],
            "approved_entity_ids": [e["id"] for e in candidates["entities"]],
        },
        headers=headers,
    )
    assert approved.status_code == 200, approved.text

    dialogue = client.get(f"/api/v1/projects/{project['id']}/dialogue-segments", headers=headers).json()
    assert len(dialogue) == 1
    assert dialogue[0]["character_name"] == "Vikram"


# -- TFD-STY-003: character/location resolution with legacy entity links ------


def test_approved_entities_resolve_into_characters_and_locations_with_a_legacy_link(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    _approve_everything(client, headers, project["id"], workflow["approval_request_id"], candidates)

    characters = client.get(f"/api/v1/projects/{project['id']}/characters", headers=headers).json()
    character_names = {c["canonical_name"] for c in characters}
    assert {"Vikram", "Priya"} <= character_names

    locations = client.get(f"/api/v1/projects/{project['id']}/locations", headers=headers).json()
    location_names = {loc["canonical_name"] for loc in locations}
    assert {"Himalayan Pass", "Monastery Archive"} <= location_names

    entities = client.get(f"/api/v1/projects/{project['id']}/entities", headers=headers).json()
    vikram_entity = next(e for e in entities if e["name"] == "Vikram")
    vikram_character = next(c for c in characters if c["canonical_name"] == "Vikram")
    assert vikram_entity["resolved_character_id"] == vikram_character["id"]

    himalayan_entity = next(e for e in entities if e["name"] == "Himalayan Pass")
    himalayan_location = next(loc for loc in locations if loc["canonical_name"] == "Himalayan Pass")
    assert himalayan_entity["resolved_location_id"] == himalayan_location["id"]


def test_the_same_character_across_two_runs_resolves_to_one_character_row(client, tenant):
    """TFD-STY-003: re-extracting the same project (e.g. a later screenplay revision)
    must reuse the existing character identity, not create a duplicate per run."""
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    _approve_everything(client, headers, project["id"], workflow["approval_request_id"], candidates)

    characters_after_first_run = client.get(f"/api/v1/projects/{project['id']}/characters", headers=headers).json()
    vikram_id_first = next(c["id"] for c in characters_after_first_run if c["canonical_name"] == "Vikram")

    # Import and run a second time against a new screenplay version with the same cast.
    from tests.support import SAMPLE_SCREENPLAY, import_screenplay_version, upload_script

    upload = upload_script(client, tenant, project["id"], content=SAMPLE_SCREENPLAY)
    version = import_screenplay_version(client, tenant, project["id"], upload.json()["asset_id"])
    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"screenplay_version_id": version["id"], "sync_execution": True},
        headers=headers,
    )
    assert trigger.status_code == 200, trigger.text
    candidates_2 = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    pending_2 = [a for a in candidates_2["approvals"] if a["status"] == "pending"]
    second_approval = next(a for a in pending_2 if a["workflow_run_id"] == trigger.json()["workflow_run_id"])
    run_2_entities = [e for e in candidates_2["entities"] if e["workflow_run_id"] == trigger.json()["workflow_run_id"]]
    run_2_scenes = [s for s in candidates_2["scenes"] if s["workflow_run_id"] == trigger.json()["workflow_run_id"]]
    client.post(
        f"/api/v1/approvals/{second_approval['id']}/decide",
        json={
            "decision": "approved",
            "approved_scene_ids": [s["id"] for s in run_2_scenes],
            "approved_entity_ids": [e["id"] for e in run_2_entities],
        },
        headers=headers,
    )

    characters_after_second_run = client.get(f"/api/v1/projects/{project['id']}/characters", headers=headers).json()
    vikram_rows = [c for c in characters_after_second_run if c["canonical_name"] == "Vikram"]
    assert len(vikram_rows) == 1
    assert vikram_rows[0]["id"] == vikram_id_first


# -- TFD-STY-002/007: non-uppercase (forced) character cue end to end ----------


def test_a_forced_non_uppercase_cue_is_recognised_end_to_end(client, tenant):
    from tests.support import create_project, import_screenplay_version, upload_script

    script = (
        "EXT. RIVERBANK - DUSK\n\n"
        "Reeds sway in the evening breeze.\n\n"
        "@Meera\n"
        "The boat leaves at midnight.\n"
    )
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    upload = upload_script(client, tenant, project["id"], content=script, filename="riverbank.fountain")
    version = import_screenplay_version(client, tenant, project["id"], upload.json()["asset_id"])

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"screenplay_version_id": version["id"], "sync_execution": True},
        headers=headers,
    )
    assert trigger.status_code == 200, trigger.text
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    assert any(e["name"] == "Meera" and e["category"] == "character" for e in candidates["entities"])

    approved = client.post(
        f"/api/v1/approvals/{trigger.json()['approval_request_id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    dialogue = client.get(f"/api/v1/projects/{project['id']}/dialogue-segments", headers=headers).json()
    assert any(d["character_name"] == "Meera" and d["line_text"] == "The boat leaves at midnight." for d in dialogue)
