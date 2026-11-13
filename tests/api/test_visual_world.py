"""D5 (Visual World): location/environment profile versioning, the legacy location
link, environment states, the Costume Bible, costume states/assignment, props/weapons,
and the minimal continuity-finding seam. Acceptance criteria cited are
docs/product/ACCEPTANCE_CRITERIA.md §3.12.
"""

from __future__ import annotations

import uuid

from packages.persistence.database import SessionLocal
from packages.persistence.models import ResearchClaimModel
from tests.support import as_actor, create_project, project_with_pending_approval


def _approve_everything(client, headers, project_id, approval_id):
    candidates = client.get(f"/api/v1/projects/{project_id}/candidates", headers=headers).json()
    return client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "approved_scene_ids": [s["id"] for s in candidates["scenes"]],
            "approved_entity_ids": [e["id"] for e in candidates["entities"]],
        },
        headers=headers,
    )


def _project_with_world(client, tenant):
    """Himalayan Pass / Monastery Archive locations, Vikram / Priya characters, and 2
    approved scenes, via D3's existing Script Intelligence pipeline."""
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    approved = _approve_everything(client, headers, project["id"], workflow["approval_request_id"])
    assert approved.status_code == 200, approved.text
    locations = client.get(f"/api/v1/projects/{project['id']}/locations", headers=headers).json()
    characters = client.get(f"/api/v1/projects/{project['id']}/characters", headers=headers).json()
    scenes = client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()
    himalayan = next(loc for loc in locations if loc["canonical_name"] == "Himalayan Pass")
    vikram = next(c for c in characters if c["canonical_name"] == "Vikram")
    return project, headers, himalayan, vikram, scenes


def _create_claim(project_id: str, org_id: str) -> str:
    claim_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            ResearchClaimModel(
                id=claim_id,
                project_id=project_id,
                organization_id=org_id,
                project_version=1,
                claim_class="historical_fact",
                statement="Himalayan caravans wore layered wool against the cold.",
            )
        )
        db.commit()
    finally:
        db.close()
    return claim_id


# -- TFD-ENV-001/004: location/environment profiles and the legacy location link ----


def test_adopting_a_location_links_matching_scenes_without_touching_location_name(client, tenant):
    project, headers, himalayan, _vikram, scenes = _project_with_world(client, tenant)
    himalayan_scene = next(s for s in scenes if s["location_name"] == "Himalayan Pass")

    adopt = client.post(f"/api/v1/projects/{project['id']}/locations/{himalayan['id']}/adopt", headers=headers)
    assert adopt.status_code == 200, adopt.text
    assert himalayan_scene["id"] in adopt.json()["matched_scene_ids"]

    scenes_after = client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()
    himalayan_scene_after = next(s for s in scenes_after if s["id"] == himalayan_scene["id"])
    assert himalayan_scene_after["location_name"] == "Himalayan Pass"  # untouched


def test_location_version_requires_source_on_every_characteristic(client, tenant):
    project, headers, himalayan, _vikram, _scenes = _project_with_world(client, tenant)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/locations/{himalayan['id']}/versions",
        json={"profile_patch": {"geography": {"value": "high mountain pass", "status": "approved"}}},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


def test_editing_a_location_never_mutates_the_approved_version(client, tenant):
    project, headers, himalayan, _vikram, _scenes = _project_with_world(client, tenant)
    location_id = himalayan["id"]

    propose_1 = client.post(
        f"/api/v1/projects/{project['id']}/locations/{location_id}/versions",
        json={"profile_patch": {"geography": {"value": "high mountain pass", "source": "screenplay", "status": "approved"}}},
        headers=headers,
    )
    assert propose_1.status_code == 201, propose_1.text
    version_1 = propose_1.json()["version"]

    decide_1 = client.post(
        f"/api/v1/projects/{project['id']}/locations/{location_id}/versions/{version_1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decide_1.status_code == 200, decide_1.text

    propose_2 = client.post(
        f"/api/v1/projects/{project['id']}/locations/{location_id}/versions",
        json={"profile_patch": {"period": {"value": "medieval", "source": "research_claim", "status": "approved"}}},
        headers=headers,
    )
    version_2 = propose_2.json()["version"]
    assert version_2["version_number"] == 2
    assert version_2["profile"]["geography"]["value"] == "high mountain pass"  # carried forward unedited

    detail_still_v1 = client.get(f"/api/v1/projects/{project['id']}/locations/{location_id}", headers=headers).json()
    assert detail_still_v1["current_version"]["version_number"] == 1


def test_environment_state_is_set_and_retrieved_for_a_scene(client, tenant):
    project, headers, _himalayan, _vikram, scenes = _project_with_world(client, tenant)
    scene_id = scenes[0]["id"]

    create = client.post(
        f"/api/v1/projects/{project['id']}/environment-states",
        json={"scene_id": scene_id, "changes": {"weather": "light rain", "time_of_day": "dusk"}},
        headers=headers,
    )
    assert create.status_code == 201, create.text

    current = client.get(
        f"/api/v1/projects/{project['id']}/environment-states", params={"scene_id": scene_id}, headers=headers
    )
    assert current.json()["changes"]["weather"] == "light rain"


# -- TFD-CST-001: Costume Bible with tenant-checked claim links ----------------------


def test_costume_version_claim_links_must_belong_to_the_same_project(client, tenant, other_tenant):
    project, headers, _himalayan, vikram, _scenes = _project_with_world(client, tenant)
    foreign_project = create_project(client, other_tenant, title="Foreign")
    foreign_claim_id = _create_claim(foreign_project["id"], other_tenant.org_id)

    costume = client.post(
        f"/api/v1/projects/{project['id']}/costumes", json={"name": "Expedition Coat", "character_id": vikram["id"]}, headers=headers
    ).json()

    blocked = client.post(
        f"/api/v1/projects/{project['id']}/costumes/{costume['id']}/versions",
        json={"claim_links": [foreign_claim_id]},
        headers=headers,
    )
    assert blocked.status_code == 404, blocked.text


def test_costume_bible_candidate_approved_into_a_version_with_linked_claims(client, tenant):
    project, headers, _himalayan, vikram, _scenes = _project_with_world(client, tenant)
    claim_1 = _create_claim(project["id"], tenant.org_id)
    claim_2 = _create_claim(project["id"], tenant.org_id)

    costume = client.post(
        f"/api/v1/projects/{project['id']}/costumes", json={"name": "Expedition Coat", "character_id": vikram["id"]}, headers=headers
    ).json()

    propose = client.post(
        f"/api/v1/projects/{project['id']}/costumes/{costume['id']}/versions",
        json={
            "profile_patch": {
                "garments": {"value": "layered wool coat", "source": "research_claim", "status": "approved"},
                "colours": {"value": "deep indigo", "source": "director", "status": "approved"},
            },
            "claim_links": [claim_1, claim_2],
        },
        headers=headers,
    )
    assert propose.status_code == 201, propose.text
    version = propose.json()["version"]
    assert version["status"] == "draft"
    assert set(version["claim_links"]) == {claim_1, claim_2}

    decided = client.post(
        f"/api/v1/projects/{project['id']}/costumes/{costume['id']}/versions/{version['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"

    detail = client.get(f"/api/v1/projects/{project['id']}/costumes/{costume['id']}", headers=headers).json()
    assert detail["current_version"]["version_number"] == 1


# -- TFD-CST-002: costume states, versioned -------------------------------------------


def test_costume_states_are_versioned(client, tenant):
    project, headers, _himalayan, vikram, _scenes = _project_with_world(client, tenant)
    costume = client.post(
        f"/api/v1/projects/{project['id']}/costumes", json={"name": "Expedition Coat", "character_id": vikram["id"]}, headers=headers
    ).json()

    clean = client.post(
        f"/api/v1/projects/{project['id']}/costumes/{costume['id']}/states",
        json={"state_label": "clean"},
        headers=headers,
    ).json()
    assert clean["version"] == 1

    battle_damaged = client.post(
        f"/api/v1/projects/{project['id']}/costumes/{costume['id']}/states",
        json={"state_label": "battle-damaged", "deltas": {"tears": True, "blood": "left sleeve"}},
        headers=headers,
    ).json()
    assert battle_damaged["version"] == 1  # a different state_label, independent version chain

    clean_edited = client.post(
        f"/api/v1/projects/{project['id']}/costumes/{costume['id']}/states",
        json={"state_label": "clean", "deltas": {"freshly_pressed": True}},
        headers=headers,
    ).json()
    assert clean_edited["version"] == 2
    assert clean_edited["supersedes_id"] == clean["id"]

    states = client.get(f"/api/v1/projects/{project['id']}/costumes/{costume['id']}/states", headers=headers).json()
    assert len(states) == 3  # both old and new "clean" versions retained


# -- TFD-CST-003: costume assignment conflicts are not silently resolved -------------


def test_assigning_two_costumes_to_the_same_character_scene_and_state_raises_a_finding(client, tenant):
    project, headers, _himalayan, vikram, scenes = _project_with_world(client, tenant)
    scene_id = scenes[0]["id"]
    coat = client.post(
        f"/api/v1/projects/{project['id']}/costumes", json={"name": "Expedition Coat"}, headers=headers
    ).json()
    robe = client.post(
        f"/api/v1/projects/{project['id']}/costumes", json={"name": "Ceremonial Robe"}, headers=headers
    ).json()

    first = client.post(
        f"/api/v1/projects/{project['id']}/costume-assignments",
        json={"character_id": vikram["id"], "scene_id": scene_id, "costume_id": coat["id"]},
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/api/v1/projects/{project['id']}/costume-assignments",
        json={"character_id": vikram["id"], "scene_id": scene_id, "costume_id": robe["id"]},
        headers=headers,
    )
    assert second.status_code == 201, second.text  # not silently resolved -- both persist

    findings = client.get(f"/api/v1/projects/{project['id']}/continuity-findings", headers=headers).json()
    assert any(f["finding_type"] == "costume_conflict" for f in findings)


# -- TFD-PRP-001/002: props and weapons ------------------------------------------------


def test_prop_kind_other_than_prop_or_weapon_is_rejected(client, tenant):
    project, headers, _himalayan, _vikram, _scenes = _project_with_world(client, tenant)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/props",
        json={"name": "Ancient Map", "kind": "scroll"},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


def test_a_weapon_stores_type_design_material_scale_and_ownership(client, tenant):
    project, headers, _himalayan, vikram, _scenes = _project_with_world(client, tenant)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/props",
        json={
            "name": "Vikram's Khanda",
            "kind": "weapon",
            "type": "sword",
            "design": "curved double-edged blade",
            "material": "forged steel",
            "scale": "life-size",
            "owner_character_id": vikram["id"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    prop = resp.json()
    assert prop["kind"] == "weapon"
    assert prop["owner_character_id"] == vikram["id"]


def test_prop_state_tracks_holder_per_scene(client, tenant):
    project, headers, _himalayan, vikram, scenes = _project_with_world(client, tenant)
    prop = client.post(
        f"/api/v1/projects/{project['id']}/props",
        json={"name": "Vikram's Khanda", "kind": "weapon"},
        headers=headers,
    ).json()

    held = client.post(
        f"/api/v1/projects/{project['id']}/props/{prop['id']}/states",
        json={"scene_id": scenes[0]["id"], "holder_character_id": vikram["id"]},
        headers=headers,
    )
    assert held.status_code == 201, held.text

    not_held = client.post(
        f"/api/v1/projects/{project['id']}/props/{prop['id']}/states",
        json={"scene_id": scenes[1]["id"], "holder_character_id": None, "notes": "left behind at the pass"},
        headers=headers,
    )
    assert not_held.status_code == 201, not_held.text

    states = client.get(f"/api/v1/projects/{project['id']}/props/{prop['id']}/states", headers=headers).json()
    assert len(states) == 2
    assert any(s["holder_character_id"] == vikram["id"] for s in states)
    assert any(s["holder_character_id"] is None for s in states)
