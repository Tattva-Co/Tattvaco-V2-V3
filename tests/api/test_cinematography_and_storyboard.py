"""D6 (Cinematography & Storyboard): the Cinematography Bible, AI shot-planning
recommendations with override, storyboard PDF ingestion, and the panel<->scene
many-to-many mapping. Acceptance criteria cited are
docs/product/ACCEPTANCE_CRITERIA.md §3.13/3.14.
"""

from __future__ import annotations

import io

from tests.support import as_actor, create_project, project_with_pending_approval


def _pdf_bytes(page_count: int) -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=400, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


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


# -- TFD-CIN-004: recommendations with rationale and override -----------------------


def test_recommendation_covers_every_required_field_and_auto_applies_nothing(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/recommendations",
        json={"intent": "warrior's first appearance at sunset, powerful, wide, epic"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    recommendation = resp.json()
    required_fields = {
        "shot_type", "position", "lens", "movement", "framing", "lighting", "background", "placement", "duration", "references",
    }
    assert required_fields <= set(recommendation["recommendation"].keys())
    for field in required_fields:
        assert recommendation["recommendation"][field]["metadata_origin"] == "recommended"
        assert recommendation["recommendation"][field]["rationale"]
    assert recommendation["overrides"] == {}


def test_overriding_a_field_is_stored_with_the_user_and_the_recommendation_is_retained(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    created = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/recommendations",
        json={"intent": "a quiet conversation between old friends"},
        headers=headers,
    ).json()
    original_lens = created["recommendation"]["lens"]["value"]

    override = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/recommendations/{created['id']}/override",
        json={"field_name": "lens", "value": "50mm prime"},
        headers=headers,
    )
    assert override.status_code == 200, override.text
    body = override.json()
    assert body["overrides"]["lens"]["value"] == "50mm prime"
    assert body["overrides"]["lens"]["overridden_by"] == tenant.user_id
    assert body["recommendation"]["lens"]["value"] == original_lens  # retained, not replaced


# -- TFD-CIN-005: Cinematography Bible ------------------------------------------------


def test_cinematography_bible_version_bundles_camera_lens_lighting_and_visual_language(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    camera = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/camera-profiles",
        json={"name": "ARRI Alexa 35", "spec_kind": "physical", "specs": {"sensor": "4.6K", "frame_rate": 24}},
        headers=headers,
    ).json()
    lens = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/lens-profiles",
        json={"name": "Cooke S4 35mm", "specs": {"focal_length_mm": 35}},
        headers=headers,
    ).json()
    lighting = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/lighting-profiles",
        json={"name": "Golden hour backlight", "specs": {"color_temp_k": 3200}},
        headers=headers,
    ).json()

    propose = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/profile/versions",
        json={
            "camera_profile_ids": [camera["id"]],
            "lens_profile_ids": [lens["id"]],
            "lighting_profile_ids": [lighting["id"]],
            "composition_rules": {"rule_of_thirds": "default"},
            "virtual_camera_profile": {"engine": "none"},
            "visual_language": {"palette": "desaturated earth tones", "film_look": "35mm anamorphic"},
        },
        headers=headers,
    )
    assert propose.status_code == 201, propose.text
    version = propose.json()["version"]
    assert version["status"] == "draft"

    decided = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/profile/versions/{version['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"

    current = client.get(f"/api/v1/projects/{project['id']}/cinematography/profile", headers=headers).json()
    assert current["id"] == version["id"]
    assert current["visual_language"]["palette"] == "desaturated earth tones"


def test_bible_version_rejects_a_camera_profile_from_another_project(client, tenant, other_tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    foreign_project = create_project(client, other_tenant, title="Foreign")
    foreign_camera = client.post(
        f"/api/v1/projects/{foreign_project['id']}/cinematography/camera-profiles",
        json={"name": "Foreign Camera", "spec_kind": "physical"},
        headers=as_actor(other_tenant.user_id),
    ).json()

    resp = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/profile/versions",
        json={"camera_profile_ids": [foreign_camera["id"]]},
        headers=headers,
    )
    assert resp.status_code == 404, resp.text


def test_camera_profile_spec_kind_other_than_physical_or_virtual_is_rejected(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/cinematography/camera-profiles",
        json={"name": "Mystery Camera", "spec_kind": "holographic"},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


# -- TFD-SB-001: storyboard image/PDF ingestion --------------------------------------


def test_ingesting_a_pdf_creates_one_panel_candidate_per_page(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    upload = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        files={"file": ("storyboard.pdf", io.BytesIO(_pdf_bytes(3)), "application/pdf")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    asset_id = upload.json()["asset_id"]

    ingest = client.post(
        f"/api/v1/projects/{project['id']}/storyboard/ingest",
        json={"source_asset_id": asset_id},
        headers=headers,
    )
    assert ingest.status_code == 201, ingest.text
    run = ingest.json()
    assert run["status"] == "awaiting_approval"
    assert run["output_refs"]["panel_count"] == 3
    assert run["output_refs"]["page_errors"] == []

    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    run_approvals = [a for a in candidates["approvals"] if a["workflow_run_id"] == run["id"]]
    assert len(run_approvals) == 1
    approval = run_approvals[0]
    assert approval["candidate_summary"]["panel_count"] == 3

    decide = client.post(
        f"/api/v1/approvals/{approval['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decide.status_code == 200, decide.text

    panels = client.get(f"/api/v1/projects/{project['id']}/storyboard/panels", headers=headers).json()
    ingested_panels = [p for p in panels if p["frame_asset_id"] is not None]
    assert len(ingested_panels) == 3


def test_ingestion_requires_a_clean_asset(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    upload = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        files={"file": ("not_a_pdf.txt", io.BytesIO(b"just text"), "text/plain")},
        headers=headers,
    )
    asset_id = upload.json()["asset_id"]

    ingest = client.post(
        f"/api/v1/projects/{project['id']}/storyboard/ingest",
        json={"source_asset_id": asset_id},
        headers=headers,
    )
    assert ingest.status_code == 422, ingest.text


# -- TFD-SB-003: many-to-many panel<->scene mapping ----------------------------------


def test_a_panel_can_be_mapped_to_multiple_scenes(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    approved = _approve_everything(client, headers, project["id"], workflow["approval_request_id"])
    assert approved.status_code == 200, approved.text
    scenes = client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()
    assert len(scenes) >= 2

    upload = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        files={"file": ("board.pdf", io.BytesIO(_pdf_bytes(1)), "application/pdf")},
        headers=headers,
    )
    ingest = client.post(
        f"/api/v1/projects/{project['id']}/storyboard/ingest",
        json={"source_asset_id": upload.json()["asset_id"]},
        headers=headers,
    ).json()
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    approval = next(a for a in candidates["approvals"] if a["workflow_run_id"] == ingest["id"])
    client.post(f"/api/v1/approvals/{approval['id']}/decide", json={"decision": "approved"}, headers=headers)

    panel = client.get(f"/api/v1/projects/{project['id']}/storyboard/panels", headers=headers).json()[0]

    first = client.post(
        f"/api/v1/projects/{project['id']}/storyboard/mappings",
        json={"panel_id": panel["id"], "scene_id": scenes[0]["id"]},
        headers=headers,
    )
    assert first.status_code == 201, first.text
    second = client.post(
        f"/api/v1/projects/{project['id']}/storyboard/mappings",
        json={"panel_id": panel["id"], "scene_id": scenes[1]["id"]},
        headers=headers,
    )
    assert second.status_code == 201, second.text

    mappings = client.get(f"/api/v1/projects/{project['id']}/storyboard/mappings", headers=headers).json()
    mapped_scene_ids = {m["scene_id"] for m in mappings if m["panel_id"] == panel["id"]}
    assert mapped_scene_ids == {scenes[0]["id"], scenes[1]["id"]}


def test_mapping_the_same_panel_to_the_same_scene_twice_is_rejected(client, tenant):
    project, workflow = project_with_pending_approval(client, tenant)
    headers = as_actor(tenant.user_id)
    _approve_everything(client, headers, project["id"], workflow["approval_request_id"])
    scenes = client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()

    upload = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        files={"file": ("board.pdf", io.BytesIO(_pdf_bytes(1)), "application/pdf")},
        headers=headers,
    )
    ingest = client.post(
        f"/api/v1/projects/{project['id']}/storyboard/ingest",
        json={"source_asset_id": upload.json()["asset_id"]},
        headers=headers,
    ).json()
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    approval = next(a for a in candidates["approvals"] if a["workflow_run_id"] == ingest["id"])
    client.post(f"/api/v1/approvals/{approval['id']}/decide", json={"decision": "approved"}, headers=headers)
    panel = client.get(f"/api/v1/projects/{project['id']}/storyboard/panels", headers=headers).json()[0]

    client.post(
        f"/api/v1/projects/{project['id']}/storyboard/mappings",
        json={"panel_id": panel["id"], "scene_id": scenes[0]["id"]},
        headers=headers,
    )
    duplicate = client.post(
        f"/api/v1/projects/{project['id']}/storyboard/mappings",
        json={"panel_id": panel["id"], "scene_id": scenes[0]["id"]},
        headers=headers,
    )
    assert duplicate.status_code == 422, duplicate.text
