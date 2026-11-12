"""Idempotency-Key on POST requests (TFD-OPS-004; plan C6)."""

from __future__ import annotations

import io
import json
from datetime import timedelta

from apps.api.idempotency import IdempotencyStore, fingerprint
from packages.persistence.database import SessionLocal
from packages.persistence.models import WorkflowRunModel
from tests.support import (
    SAMPLE_SCREENPLAY,
    as_actor,
    create_project,
    import_screenplay_version,
    upload_script,
)

PROJECT = {"title": "Idempotent Film", "logline": "Once.", "genre": "Drama"}


def _projects(client, tenant) -> list:
    return client.get("/api/v1/projects", headers=as_actor(tenant.user_id)).json()


def _post_project(client, tenant, key: str | None, body: dict = PROJECT):
    headers = as_actor(tenant.user_id)
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post("/api/v1/projects", json=body, headers=headers)


def test_retry_with_same_key_replays_the_first_response_and_creates_once(client, tenant):
    first = _post_project(client, tenant, "create-1")
    second = _post_project(client, tenant, "create-1")
    assert first.status_code == second.status_code == 201
    assert second.json() == first.json()
    assert second.headers.get("Idempotent-Replayed") == "true"
    assert "Idempotent-Replayed" not in first.headers
    assert [p["id"] for p in _projects(client, tenant)] == [first.json()["id"]]


def test_without_a_key_each_post_runs(client, tenant):
    assert _post_project(client, tenant, None).status_code == 201
    assert _post_project(client, tenant, None).status_code == 201
    assert len(_projects(client, tenant)) == 2


def test_same_key_with_a_different_body_is_rejected(client, tenant):
    assert _post_project(client, tenant, "k").status_code == 201
    reused = _post_project(client, tenant, "k", {**PROJECT, "title": "Something else"})
    assert reused.status_code == 422
    assert reused.json()["error"] == "IdempotencyKeyReused"
    assert len(_projects(client, tenant)) == 1


def test_keys_are_scoped_per_user(client, tenant, other_tenant):
    mine = _post_project(client, tenant, "shared-key")
    theirs = _post_project(client, other_tenant, "shared-key")
    assert mine.status_code == theirs.status_code == 201
    assert mine.json()["id"] != theirs.json()["id"]
    assert "Idempotent-Replayed" not in theirs.headers


def test_a_key_still_in_progress_returns_409(client, tenant):
    # Claim the key the way a first, still-running attempt would, then retry it.
    body = json.dumps(PROJECT).encode()
    claim = IdempotencyStore(timedelta(hours=1)).claim(
        tenant.org_id, tenant.user_id, "busy", "POST", "/api/v1/projects",
        fingerprint("POST", "/api/v1/projects", b"", "application/json", body),
    )
    assert claim.outcome == "new"
    resp = client.post(
        "/api/v1/projects", content=body,
        headers={**as_actor(tenant.user_id), "Idempotency-Key": "busy", "Content-Type": "application/json"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "IdempotencyKeyInProgress"
    assert _projects(client, tenant) == []


def test_multipart_upload_retry_replays_despite_a_new_boundary(client, tenant):
    project = create_project(client, tenant)
    headers = {**as_actor(tenant.user_id), "Idempotency-Key": "upload-1"}

    def upload():
        return client.post(
            f"/api/v1/projects/{project['id']}/assets/upload",
            files={"file": ("chronicle.fountain", io.BytesIO(SAMPLE_SCREENPLAY.encode()), "text/plain")},
            headers=headers,
        )

    first, second = upload(), upload()
    assert first.status_code == second.status_code == 200
    assert second.json()["asset_id"] == first.json()["asset_id"]
    assert second.headers.get("Idempotent-Replayed") == "true"
    assets = client.get(f"/api/v1/projects/{project['id']}/assets", headers=as_actor(tenant.user_id)).json()
    assert len(assets) == 1


def test_workflow_trigger_retry_starts_one_run(client, tenant):
    project = create_project(client, tenant)
    asset_id = upload_script(client, tenant, project["id"]).json()["asset_id"]
    version_id = import_screenplay_version(client, tenant, project["id"], asset_id)["id"]
    headers = {**as_actor(tenant.user_id), "Idempotency-Key": "trigger-1"}
    body = {"screenplay_version_id": version_id}
    first = client.post(f"/api/v1/projects/{project['id']}/workflows/script-intelligence", json=body, headers=headers)
    second = client.post(f"/api/v1/projects/{project['id']}/workflows/script-intelligence", json=body, headers=headers)
    assert first.status_code == second.status_code
    assert second.json()["workflow_run_id"] == first.json()["workflow_run_id"]
    db = SessionLocal()
    try:
        assert db.query(WorkflowRunModel).filter_by(project_id=project["id"]).count() == 1
    finally:
        db.close()


def test_malformed_key_is_rejected(client, tenant):
    resp = _post_project(client, tenant, "x" * 256)
    assert resp.status_code == 400
    assert resp.json()["error"] == "InvalidIdempotencyKey"
