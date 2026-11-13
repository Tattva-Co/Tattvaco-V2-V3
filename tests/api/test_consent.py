"""D4 (Character & Digital Human, V1 foundation): performer registry, consent and the
voice-profile consent gate. Acceptance criteria cited are
docs/product/ACCEPTANCE_CRITERIA.md §3.11 (and the TFD-CHR-002.2/TFD-PHY-006.1 gates in
§3.8/3.9, exercised here against a performer-linked character).
"""

from __future__ import annotations

import pytest

from packages.core.config import get_settings
from tests.support import as_actor, create_project


@pytest.fixture
def consent_policy_approved():
    """DEC-007/DEC-012 are both open as of this build (AT-CNS-002.2's default state);
    flip the gate only for the tests that exercise what happens once Legal approves it,
    and always restore the real default afterwards."""
    settings = get_settings()
    before = (settings.dec_007_retention_policy_approved, settings.dec_012_consent_template_approved)
    settings.dec_007_retention_policy_approved = True
    settings.dec_012_consent_template_approved = True
    yield
    settings.dec_007_retention_policy_approved, settings.dec_012_consent_template_approved = before


# -- AT-CNS-002.2: performer/consent creation blocked while policy is pending -------


def test_performer_creation_is_blocked_while_consent_policy_is_pending(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    resp = client.post(f"/api/v1/projects/{project['id']}/performers", json={"display_name": "Arjun Rao"}, headers=headers)
    assert resp.status_code == 403, resp.text
    assert "policy_pending" in resp.text


# -- Everything below exercises the real workflow once Legal approves the policy ----


def test_performer_and_consent_lifecycle(client, tenant, consent_policy_approved):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)

    performer = client.post(
        f"/api/v1/projects/{project['id']}/performers", json={"display_name": "Arjun Rao"}, headers=headers
    )
    assert performer.status_code == 201, performer.text
    performer_id = performer.json()["id"]

    created = client.post(
        f"/api/v1/projects/{project['id']}/performers/{performer_id}/consents",
        json={"purpose": "reference_storage"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    consent = created.json()["consent"]
    assert consent["status"] == "draft"  # AT-CNS-002.1: starts in draft

    check_before = client.get(
        f"/api/v1/projects/{project['id']}/consent-checks",
        params={"performer_id": performer_id, "purpose": "reference_storage"},
        headers=headers,
    ).json()
    assert check_before["allowed"] is False

    decided = client.post(
        f"/api/v1/projects/{project['id']}/consents/{consent['id']}/decide", json={"decision": "approved"}, headers=headers
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "active"

    check_after = client.get(
        f"/api/v1/projects/{project['id']}/consent-checks",
        params={"performer_id": performer_id, "purpose": "reference_storage"},
        headers=headers,
    ).json()
    assert check_after["allowed"] is True


def test_revoking_one_purpose_leaves_a_sibling_purpose_active(client, tenant, consent_policy_approved):
    """AT-CNS-004.1: consent for {digital_double, voice_clone} -- modelled as two sibling
    rows (DEC-059) -- revoking one never touches the other."""
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    performer_id = client.post(
        f"/api/v1/projects/{project['id']}/performers", json={"display_name": "Meera Nair"}, headers=headers
    ).json()["id"]

    for purpose in ("digital_double", "voice_clone"):
        created = client.post(
            f"/api/v1/projects/{project['id']}/performers/{performer_id}/consents",
            json={"purpose": purpose},
            headers=headers,
        ).json()
        client.post(
            f"/api/v1/projects/{project['id']}/consents/{created['consent']['id']}/decide",
            json={"decision": "approved"},
            headers=headers,
        )

    revoke = client.post(
        f"/api/v1/projects/{project['id']}/consents/revoke",
        json={"performer_id": performer_id, "purpose": "digital_double", "reason": "contract ended"},
        headers=headers,
    )
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["status"] == "revoked"

    digital_double_check = client.get(
        f"/api/v1/projects/{project['id']}/consent-checks",
        params={"performer_id": performer_id, "purpose": "digital_double"},
        headers=headers,
    ).json()
    voice_clone_check = client.get(
        f"/api/v1/projects/{project['id']}/consent-checks",
        params={"performer_id": performer_id, "purpose": "voice_clone"},
        headers=headers,
    ).json()
    assert digital_double_check["allowed"] is False
    assert voice_clone_check["allowed"] is True  # untouched by the digital_double revocation


# -- TFD-CNS-005: voice consent is separate from storage consent --------------------


def test_voice_clone_requires_its_own_consent_not_reference_storage(client, tenant, consent_policy_approved):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    performer_id = client.post(
        f"/api/v1/projects/{project['id']}/performers", json={"display_name": "Kabir Shah"}, headers=headers
    ).json()["id"]

    # Grant only reference_storage, not voice_clone.
    created = client.post(
        f"/api/v1/projects/{project['id']}/performers/{performer_id}/consents",
        json={"purpose": "reference_storage"},
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/projects/{project['id']}/consents/{created['consent']['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )

    blocked = client.post(
        f"/api/v1/projects/{project['id']}/voice-profiles",
        json={"kind": "clone", "performer_id": performer_id},
        headers=headers,
    )
    assert blocked.status_code == 403, blocked.text
    assert "consent_required: voice_clone" in blocked.text

    voice_consent = client.post(
        f"/api/v1/projects/{project['id']}/performers/{performer_id}/consents",
        json={"purpose": "voice_clone"},
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/projects/{project['id']}/consents/{voice_consent['consent']['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )

    allowed = client.post(
        f"/api/v1/projects/{project['id']}/voice-profiles",
        json={"kind": "clone", "performer_id": performer_id},
        headers=headers,
    )
    assert allowed.status_code == 201, allowed.text


def test_original_recording_voice_profile_needs_no_consent(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/voice-profiles", json={"kind": "original_recording"}, headers=headers
    )
    assert resp.status_code == 201, resp.text


# -- TFD-CHR-002.2/TFD-PHY-006.1 gates, now exercised with real consent in play ------


def test_facial_reference_is_blocked_then_allowed_once_the_performer_has_active_consent(client, tenant, consent_policy_approved):
    from packages.persistence.database import SessionLocal
    from packages.persistence.models import CharacterModel

    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    performer_id = client.post(
        f"/api/v1/projects/{project['id']}/performers", json={"display_name": "Zara Khan"}, headers=headers
    ).json()["id"]

    db = SessionLocal()
    try:
        character = CharacterModel(project_id=project["id"], organization_id=tenant.org_id, canonical_name="Zara", performer_id=performer_id)
        db.add(character)
        db.commit()
        character_id = character.id
    finally:
        db.close()

    upload = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        files={"file": ("zara_front.txt", b"placeholder asset", "text/plain")},
        headers=headers,
    )
    asset_id = upload.json()["asset_id"]

    blocked = client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/facial-references",
        json={"asset_id": asset_id, "role": "identity_front"},
        headers=headers,
    )
    assert blocked.status_code == 403, blocked.text
    assert "consent_required: reference_storage" in blocked.text

    created = client.post(
        f"/api/v1/projects/{project['id']}/performers/{performer_id}/consents",
        json={"purpose": "reference_storage"},
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/projects/{project['id']}/consents/{created['consent']['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )

    allowed = client.post(
        f"/api/v1/projects/{project['id']}/characters/{character_id}/facial-references",
        json={"asset_id": asset_id, "role": "identity_front"},
        headers=headers,
    )
    assert allowed.status_code == 201, allowed.text
