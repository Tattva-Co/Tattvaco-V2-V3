"""Durable outbox path: API queues a run, the worker claims and executes it."""

import opentelemetry.trace as otel_trace
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from apps.worker.worker import process_one_task
from packages.persistence.database import session_scope
from packages.persistence.models import OutboxTaskModel
from tests.support import (
    as_actor,
    create_draft_screenplay_version,
    create_project,
    import_screenplay_version,
    upload_script,
)


def _drain(max_tasks: int = 20) -> None:
    for _ in range(max_tasks):
        if not process_one_task("test-worker"):
            return


@pytest.fixture
def trace_exporter():
    """See tests/unit/test_tracing.py for why this resets OTel's global TracerProvider
    rather than relying on configure_tracing: it is a once-per-process singleton, and
    another test may already have set it (e.g. by building the FastAPI app)."""
    previous_provider = otel_trace._TRACER_PROVIDER
    previous_done = otel_trace._TRACER_PROVIDER_SET_ONCE._done
    otel_trace._TRACER_PROVIDER = None
    otel_trace._TRACER_PROVIDER_SET_ONCE._done = False

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    otel_trace.set_tracer_provider(provider)

    yield exporter

    otel_trace._TRACER_PROVIDER = previous_provider
    otel_trace._TRACER_PROVIDER_SET_ONCE._done = previous_done


def test_queued_run_is_executed_by_worker(client, tenant):
    headers = as_actor(tenant.user_id)
    project = create_project(client, tenant)
    asset_id = upload_script(client, tenant, project["id"]).json()["asset_id"]
    version_id = import_screenplay_version(client, tenant, project["id"], asset_id)["id"]

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"screenplay_version_id": version_id, "sync_execution": False},
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
    # An empty screenplay version's text is a reliable, deterministic way to make the
    # *workflow* fail business-rule validation inside the worker, bypassing the normal
    # upload/import flow (both of which already reject empty or unsupported content
    # before a screenplay_versions row would ever exist -- see
    # test_assets_api.py::test_empty_upload_is_rejected and
    # test_screenplay_import_refuses_assets_with_no_supported_extraction).
    version_id = create_draft_screenplay_version(project["id"], tenant.org_id, tenant.user_id, content_text="")

    run_id = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"screenplay_version_id": version_id, "sync_execution": False},
        headers=headers,
    ).json()["workflow_run_id"]

    _drain()

    run = client.get(f"/api/v1/workflow-runs/{run_id}", headers=headers).json()
    assert run["status"] == "failed"
    assert "empty" in run["error_message"]
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


def test_the_api_trigger_and_the_worker_that_processes_it_share_one_trace(client, tenant, trace_exporter):
    """C9 exit criterion, exercised through the REAL enqueue -> claim path (not just the
    tracing primitives in isolation -- tests/unit/test_tracing.py covers those). This is
    exactly the scenario a live docker-compose run caught a real bug in: the trace
    context was being injected into the outbox task's payload correctly, but
    apps/worker/worker.py was reading it back from the wrong key and silently falling
    back to an unrelated root span every time.

    Compares the worker's span against the `traceparent` actually persisted in the
    outbox task's payload (the real hand-off point), not against the API's own
    auto-instrumented request span: `apps.api.main.app` is built once at import time, so
    its FastAPIInstrumentor-wrapped middleware is already bound to whatever
    TracerProvider was global *then* (opentelemetry-instrumentation-asgi reads it once,
    in `__init__`, not per request) -- `trace_exporter` below swaps the provider for this
    test, but cannot retroactively change what that already-constructed middleware
    reports to. The persisted `traceparent` has no such problem: it is written by
    `inject_trace_context` at request-handling time, after the swap, using whatever span
    is actually active then."""
    headers = as_actor(tenant.user_id)
    project = create_project(client, tenant)
    asset_id = upload_script(client, tenant, project["id"]).json()["asset_id"]
    version_id = import_screenplay_version(client, tenant, project["id"], asset_id)["id"]

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"screenplay_version_id": version_id, "sync_execution": False},
        headers=headers,
    )
    assert trigger.status_code == 200, trigger.text
    run_id = trigger.json()["workflow_run_id"]

    with session_scope() as db:
        task = db.query(OutboxTaskModel).filter_by(workflow_run_id=run_id).one()
        traceparent = (task.payload or {}).get("traceparent")
    assert traceparent, f"enqueue did not persist a traceparent; payload was {task.payload!r}"
    expected_trace_id = int(traceparent.split("-")[1], 16)

    _drain()

    worker_span = next(
        (s for s in trace_exporter.get_finished_spans() if s.name == "worker.process_task:script_intelligence"),
        None,
    )
    assert worker_span is not None, "no worker span was recorded"
    assert worker_span.context.trace_id == expected_trace_id, (
        "the worker's span must belong to the trace recorded in the outbox task's own "
        "traceparent, not an unrelated root span"
    )
