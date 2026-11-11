"""Upload policy and Script Intelligence input validation at the API boundary."""

from apps.api.dependencies import get_settings
from apps.api.main import app
from packages.core.config import Settings
from tests.support import as_actor, create_project, upload_script


def test_fountain_upload_with_generic_content_type_is_accepted(client, tenant):
    project = create_project(client, tenant)
    resp = upload_script(client, tenant, project["id"], mime="application/octet-stream")
    assert resp.status_code == 200, resp.text
    assert resp.json()["mime_type"] == "text/plain"

    assets = client.get(f"/api/v1/projects/{project['id']}/assets", headers=as_actor(tenant.user_id)).json()
    assert [a["id"] for a in assets] == [resp.json()["asset_id"]]


def test_disallowed_media_type_is_rejected(client, tenant):
    project = create_project(client, tenant)
    resp = upload_script(client, tenant, project["id"], filename="clip.mp4", mime="video/mp4")
    assert resp.status_code == 415


def test_empty_upload_is_rejected(client, tenant):
    project = create_project(client, tenant)
    resp = upload_script(client, tenant, project["id"], content="")
    assert resp.status_code == 422


def test_oversized_upload_is_rejected(client, tenant):
    project = create_project(client, tenant)
    app.dependency_overrides[get_settings] = lambda: Settings(storage_max_upload_bytes=10)
    try:
        resp = upload_script(client, tenant, project["id"])
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 413


def test_script_intelligence_refuses_assets_with_no_supported_extraction(client, tenant):
    """application/json is upload-allowed (e.g. for structured metadata attachments) but
    is neither plain-text/Fountain nor one of the formats C7 added extraction for
    (PDF/DOCX/FDX) -- Script Intelligence must still refuse it, with a clear reason."""
    project = create_project(client, tenant)
    upload = upload_script(client, tenant, project["id"], filename="script.json", mime="application/json")
    assert upload.status_code == 200

    resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        # Explicit: this test checks a validation error surfaced synchronously in the
        # response. Workflows are async by default (C6); the error would otherwise only
        # appear later in the outbox task, not in this request.
        json={"script_asset_id": upload.json()["asset_id"], "sync_execution": True},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 422
    assert "plain-text" in resp.json()["detail"]


def test_unknown_asset_is_not_found(client, tenant):
    project = create_project(client, tenant)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"script_asset_id": "missing"},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 404
