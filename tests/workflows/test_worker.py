"""Durable outbox path: API queues a run, the worker claims and executes it."""

from apps.worker.worker import process_one_task
from packages.persistence.database import session_scope
from packages.persistence.models import OutboxTaskModel
from tests.support import as_actor, create_project, upload_script


def _drain(max_tasks: int = 20) -> None:
    for _ in range(max_tasks):
        if not process_one_task("test-worker"):
            return


def test_queued_run_is_executed_by_worker(client, tenant):
    headers = as_actor(tenant.user_id)
    project = create_project(client, tenant)
    asset_id = upload_script(client, tenant, project["id"]).json()["asset_id"]

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"script_asset_id": asset_id, "sync_execution": False},
        headers=headers,
    )
    assert trigger.status_code == 200
    assert trigger.json()["status"] == "queued"
    run_id = trigger.json()["workflow_run_id"]

    _drain()

    run = client.get(f"/api/v1/workflow-runs/{run_id}", headers=headers).json()
    assert run["status"] == "awaiting_approval"
    approvals = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()["approvals"]
    assert [a["status"] for a in approvals] == ["pending"]

    with session_scope() as db:
        task = db.query(OutboxTaskModel).filter_by(workflow_run_id=run_id).one()
        assert task.status == "completed"
        assert task.attempts == 1


def test_failed_run_marks_task_and_run_failed(client, tenant):
    headers = as_actor(tenant.user_id)
    project = create_project(client, tenant)
    # application/json is upload-allowed but not a format Script Intelligence (or its C7
    # text-extraction additions) supports -- a reliable, deterministic way to make the
    # *workflow* fail business-rule validation without the *upload* itself being rejected.
    asset_id = upload_script(client, tenant, project["id"], filename="s.json", mime="application/json").json()[
        "asset_id"
    ]

    run_id = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"script_asset_id": asset_id, "sync_execution": False},
        headers=headers,
    ).json()["workflow_run_id"]

    _drain()

    run = client.get(f"/api/v1/workflow-runs/{run_id}", headers=headers).json()
    assert run["status"] == "failed"
    assert "plain-text" in run["error_message"]
    with session_scope() as db:
        # A business-rule error (wrong file type) is dead-lettered immediately rather
        # than retried: the same file will fail identically on every attempt (C6).
        task = db.query(OutboxTaskModel).filter_by(workflow_run_id=run_id).one()
        assert task.status == "dead_lettered"
        assert task.attempts == 1
        assert task.last_error_class == "ValidationFailure"


def test_queued_historical_research_run_is_executed_by_worker(client, tenant):
    headers = as_actor(tenant.user_id)
    project = create_project(client, tenant, title="Async Research")

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/historical-research",
        json={"topic": "Kalinga c. 261 BCE", "sync_execution": False},
        headers=headers,
    )
    assert trigger.status_code == 200
    assert trigger.json()["status"] == "queued"
    run_id = trigger.json()["workflow_run_id"]

    _drain()

    run = client.get(f"/api/v1/workflow-runs/{run_id}", headers=headers).json()
    assert run["status"] == "awaiting_approval"

    with session_scope() as db:
        task = db.query(OutboxTaskModel).filter_by(workflow_run_id=run_id).one()
        assert task.status == "completed"
        assert task.attempts == 1


def test_queued_storyboard_run_is_executed_by_worker(client, tenant):
    headers = as_actor(tenant.user_id)
    project = create_project(client, tenant, title="Async Storyboard")

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/storyboard-intelligence",
        json={"brief": "Async storyboard sequence", "sync_execution": False},
        headers=headers,
    )
    assert trigger.status_code == 200
    assert trigger.json()["status"] == "queued"
    run_id = trigger.json()["workflow_run_id"]

    _drain()

    run = client.get(f"/api/v1/workflow-runs/{run_id}", headers=headers).json()
    assert run["status"] == "awaiting_approval"

    with session_scope() as db:
        task = db.query(OutboxTaskModel).filter_by(workflow_run_id=run_id).one()
        assert task.status == "completed"
        assert task.attempts == 1


def test_queued_film_bible_run_is_executed_by_worker(client, tenant):
    headers = as_actor(tenant.user_id)
    project = create_project(client, tenant, title="Async Film Bible")

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/film-bible-synthesis",
        json={"user_notes": "Async visual world", "sync_execution": False},
        headers=headers,
    )
    assert trigger.status_code == 200
    assert trigger.json()["status"] == "queued"
    run_id = trigger.json()["workflow_run_id"]

    _drain()

    run = client.get(f"/api/v1/workflow-runs/{run_id}", headers=headers).json()
    assert run["status"] == "awaiting_approval"

    with session_scope() as db:
        task = db.query(OutboxTaskModel).filter_by(workflow_run_id=run_id).one()
        assert task.status == "completed"
        assert task.attempts == 1
