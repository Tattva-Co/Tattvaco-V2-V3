"""D4 (Character & Digital Human, V1 foundation): identity/physical profile
versioning, facial references, scene-anchored states, and body measurements.
Acceptance criteria cited are docs/product/ACCEPTANCE_CRITERIA.md §3.8/3.9.
"""

from __future__ import annotations

import uuid

from packages.persistence.database import SessionLocal
from packages.persistence.models import MembershipModel, UserModel
from tests.support import as_actor, project_with_pending_approval


def _add_org_member(org_id: str) -> tuple[str, str]:
    user_id = str(uuid.uuid4())
    email = f"{user_id[:8]}@verifier.example"
    db = SessionLocal()
    try:
        db.add(UserModel(id=user_id, organization_id=org_id, email=email, full_name="Verifier", role="creator"))
        db.flush()
        db.add(MembershipModel(user_id=user_id, organization_id=org_id, org_role="member", status="active"))
        db.commit()
    finally:
        db.close()
    return user_id, email


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


def _project_with_characters(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    approved = _approve_everything(client, headers, project["id"], workflow["approval_request_id"])
    assert approved.status_code == 200, approved.text
    characters = client.get(f"/api/v1/projects/{project['id']}/characters", headers=headers).json()
    vikram = next(c for c in characters if c["canonical_name"] == "Vikram")
    return project, headers, vikram


# -- TFD-CHR-001/005/006: identity profile, provenance envelope, versioning ---------


def test_character_version_requires_source_on_every_characteristic(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/characters/{vikram['id']}/versions",
        json={"identity_patch": {"biography": {"value": "A cartographer.", "status": "approved"}}},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


def test_editing_a_character_never_mutates_the_approved_version(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    character_id = vikram["id"]

    propose_1 = client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/versions",
        json={
            "identity_patch": {
                "biography": {"value": "A cartographer mapping the Himalayas.", "source": "director", "status": "approved"}
            }
        },
        headers=headers,
    )
    assert propose_1.status_code == 201, propose_1.text
    version_1 = propose_1.json()["version"]
    assert version_1["version_number"] == 1
    assert version_1["status"] == "draft"

    decide_1 = client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/versions/{version_1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decide_1.status_code == 200, decide_1.text
    assert decide_1.json()["status"] == "approved"

    detail = client.get(f"/api/v1/projects/{project['id']}/characters/{character_id}", headers=headers).json()
    assert detail["current_version"]["version_number"] == 1
    assert detail["current_version"]["identity_profile"]["biography"]["value"] == "A cartographer mapping the Himalayas."

    # AT-CHR-006.1: editing a field creates a new draft; version 1 stays untouched.
    propose_2 = client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/versions",
        json={"identity_patch": {"biography": {"value": "A master cartographer.", "source": "director", "status": "approved"}}},
        headers=headers,
    )
    version_2 = propose_2.json()["version"]
    assert version_2["version_number"] == 2
    assert version_2["status"] == "draft"

    detail_still_v1 = client.get(f"/api/v1/projects/{project['id']}/characters/{character_id}", headers=headers).json()
    assert detail_still_v1["current_version"]["version_number"] == 1
    assert detail_still_v1["current_version"]["identity_profile"]["biography"]["value"] == "A cartographer mapping the Himalayas."

    decide_2 = client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/versions/{version_2['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decide_2.status_code == 200, decide_2.text

    detail_now_v2 = client.get(f"/api/v1/projects/{project['id']}/characters/{character_id}", headers=headers).json()
    assert detail_now_v2["current_version"]["version_number"] == 2

    versions = client.get(f"/api/v1/projects/{project['id']}/characters/{character_id}/versions", headers=headers).json()
    assert len(versions) == 2
    v1_in_history = next(v for v in versions if v["version_number"] == 1)
    assert v1_in_history["identity_profile"]["biography"]["value"] == "A cartographer mapping the Himalayas."
    assert v1_in_history["status"] == "approved"  # still approved, just no longer current


def test_physical_patch_fields_carry_forward_unedited_across_versions(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    character_id = vikram["id"]

    propose_1 = client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/versions",
        json={
            "identity_patch": {"role": {"value": "protagonist", "source": "director", "status": "approved"}},
            "physical_patch": {"height": {"value": "180cm", "source": "director", "status": "estimated", "confidence": 0.6}},
        },
        headers=headers,
    )
    version_1 = propose_1.json()["version"]
    client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/versions/{version_1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )

    # Edit only identity this time; the physical facet (height) must still carry forward.
    propose_2 = client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/versions",
        json={"identity_patch": {"biography": {"value": "New backstory.", "source": "director", "status": "approved"}}},
        headers=headers,
    )
    version_2 = propose_2.json()["version"]
    assert version_2["physical_profile"]["height"]["value"] == "180cm"
    assert version_2["identity_profile"]["role"]["value"] == "protagonist"


# -- TFD-CHR-002: facial identity references + consent gate --------------------------


def test_adding_a_facial_reference_with_no_linked_performer_needs_no_consent(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    upload = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        files={"file": ("vikram_front.txt", b"not a real image, just a placeholder asset", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    asset_id = upload.json()["asset_id"]

    resp = client.post(
        f"/api/v1/projects/{project['id']}/characters/{vikram['id']}/facial-references",
        json={"asset_id": asset_id, "role": "identity_front", "facial_identity_version": 1},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    refs = client.get(f"/api/v1/projects/{project['id']}/characters/{vikram['id']}/facial-references", headers=headers).json()
    assert len(refs) == 1
    assert refs[0]["role"] == "identity_front"


# -- TFD-CHR-007: character states anchored to scenes ---------------------------------


def test_character_state_effective_resolution_by_scene_number(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    scenes = client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()
    himalayan_scene = next(s for s in scenes if s["scene_number"] == 1)
    monastery_scene = next(s for s in scenes if s["scene_number"] == 2)

    create = client.post(
        f"/api/v1/projects/{project['id']}/characters/{vikram['id']}/states",
        json={
            "state_label": "wounded left arm",
            "applies_from_scene_id": monastery_scene["id"],
            "deltas": {"injury": {"location": "left forearm", "severity": "bandaged"}},
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text

    before = client.get(
        f"/api/v1/projects/{project['id']}/characters/{vikram['id']}/effective-state",
        params={"scene_number": himalayan_scene["scene_number"]},
        headers=headers,
    )
    assert before.json() is None

    at_and_after = client.get(
        f"/api/v1/projects/{project['id']}/characters/{vikram['id']}/effective-state",
        params={"scene_number": monastery_scene["scene_number"]},
        headers=headers,
    )
    assert at_and_after.json()["state_label"] == "wounded left arm"

    later = client.get(
        f"/api/v1/projects/{project['id']}/characters/{vikram['id']}/effective-state",
        params={"scene_number": monastery_scene["scene_number"] + 5},
        headers=headers,
    )
    assert later.json()["state_label"] == "wounded left arm"  # still in effect, nothing superseded it


# -- TFD-PHY-001/002/003/004: measurements -------------------------------------------


def test_measurement_requires_a_unit(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/measurements",
        json={
            "subject_type": "character_version",
            "subject_id": vikram["id"],
            "measurement_key": "height",
            "value": 180,
            "capture_method": "manual_entry",
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


def test_ai_estimate_is_capped_low_confidence_and_cannot_be_verified_without_a_scan(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    save = client.post(
        f"/api/v1/projects/{project['id']}/measurements",
        json={
            "subject_type": "character_version",
            "subject_id": vikram["id"],
            "measurement_key": "height",
            "value": 181.5,
            "unit": "cm",
            "capture_method": "ai_estimate",
            "confidence": 0.95,
        },
        headers=headers,
    )
    assert save.status_code == 201, save.text
    measurement = save.json()
    assert measurement["status"] == "estimated"
    assert measurement["confidence"] <= 0.5  # AT-PHY-004.1: capped low regardless of what was requested

    verify = client.post(
        f"/api/v1/projects/{project['id']}/measurements/{measurement['id']}/verify", headers=headers
    )
    assert verify.status_code == 422, verify.text
    assert "calibrated_capture_required" in verify.text


def test_the_same_person_cannot_verify_their_own_measurement(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    save = client.post(
        f"/api/v1/projects/{project['id']}/measurements",
        json={
            "subject_type": "character_version",
            "subject_id": vikram["id"],
            "measurement_key": "chest_circumference",
            "value": 98.0,
            "unit": "cm",
            "capture_method": "calibrated_scan",
        },
        headers=headers,
    )
    measurement = save.json()

    same_person = client.post(f"/api/v1/projects/{project['id']}/measurements/{measurement['id']}/verify", headers=headers)
    assert same_person.status_code == 409, same_person.text


def test_a_calibrated_scan_can_be_verified_by_a_different_person(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    verifier_id, verifier_email = _add_org_member(tenant.org_id)
    add_member = client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"email": verifier_email, "role_template_key": "director"},
        headers=headers,
    )
    assert add_member.status_code == 201, add_member.text

    save = client.post(
        f"/api/v1/projects/{project['id']}/measurements",
        json={
            "subject_type": "character_version",
            "subject_id": vikram["id"],
            "measurement_key": "chest_circumference",
            "value": 98.0,
            "unit": "cm",
            "capture_method": "calibrated_scan",
        },
        headers=headers,
    )
    measurement = save.json()

    verified = client.post(
        f"/api/v1/projects/{project['id']}/measurements/{measurement['id']}/verify", headers=as_actor(verifier_id)
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"
    assert verified.json()["verified_by"] == verifier_id


def test_correcting_a_measurement_keeps_both_versions_visible(client, tenant):
    project, headers, vikram = _project_with_characters(client, tenant)
    save = client.post(
        f"/api/v1/projects/{project['id']}/measurements",
        json={
            "subject_type": "character_version",
            "subject_id": vikram["id"],
            "measurement_key": "waist_circumference",
            "value": 80.0,
            "unit": "cm",
            "capture_method": "manual_entry",
        },
        headers=headers,
    )
    original = save.json()

    corrected = client.post(
        f"/api/v1/projects/{project['id']}/measurements/{original['id']}/correct",
        json={"value": 82.5, "notes": "re-measured with a proper tape"},
        headers=headers,
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["supersedes_id"] == original["id"]
    assert corrected.json()["version"] == original["version"] + 1

    history = client.get(
        f"/api/v1/projects/{project['id']}/measurements",
        params={"subject_type": "character_version", "subject_id": vikram["id"]},
        headers=headers,
    ).json()
    waist_rows = [m for m in history if m["measurement_key"] == "waist_circumference"]
    assert len(waist_rows) == 2
    assert any(m["id"] == original["id"] and m["status"] == "superseded" for m in waist_rows)
    assert any(m["id"] == corrected.json()["id"] and m["status"] == "measured" for m in waist_rows)
