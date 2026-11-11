"""C9: one trace spans API -> outbox -> worker.

OpenTelemetry's global TracerProvider is a process-wide singleton that can only be set
once (by design -- see opentelemetry.trace._set_tracer_provider). Since other tests in
this suite build a FastAPI app (packages.core.tracing.configure_tracing is called from
apps/api/main.py's create_app) before this file's tests run, `_reset_global_tracer`
below resets that singleton's internal guard for the duration of each test here and
restores whatever was there before -- the only way to install a controlled, in-memory
exporter without depending on test execution order.
"""

from __future__ import annotations

import opentelemetry.trace as otel_trace
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from packages.core.tracing import continue_trace, inject_trace_context


@pytest.fixture
def exporter():
    previous_provider = otel_trace._TRACER_PROVIDER
    previous_done = otel_trace._TRACER_PROVIDER_SET_ONCE._done
    otel_trace._TRACER_PROVIDER = None
    otel_trace._TRACER_PROVIDER_SET_ONCE._done = False

    test_exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(test_exporter))
    otel_trace.set_tracer_provider(provider)

    yield test_exporter

    otel_trace._TRACER_PROVIDER = previous_provider
    otel_trace._TRACER_PROVIDER_SET_ONCE._done = previous_done


def test_a_span_started_from_an_injected_context_shares_the_trace_id(exporter):
    """Simulates the real API -> worker boundary: one span represents "the API enqueuing
    a workflow run", its context is captured into a plain dict (what
    OutboxTaskModel.payload['trace_context'] actually holds), and a later, independent
    span represents "the worker processing that task" -- started from that captured
    context, as continue_trace does for every claimed task."""
    tracer = otel_trace.get_tracer("test.api")
    with tracer.start_as_current_span("api.enqueue_workflow_run") as api_span:
        carrier = inject_trace_context({})
        api_trace_id = api_span.get_span_context().trace_id

    # The "worker process" picks the task up later -- a different call stack entirely,
    # with only `carrier` (the persisted payload) connecting it back.
    with continue_trace(carrier, span_name="worker.process_task:script_intelligence", tracer_name="worker"):
        pass

    spans = exporter.get_finished_spans()
    names = {s.name: s for s in spans}
    assert "api.enqueue_workflow_run" in names
    assert "worker.process_task:script_intelligence" in names

    worker_span = names["worker.process_task:script_intelligence"]
    assert worker_span.context.trace_id == api_trace_id, (
        "the worker's span must belong to the SAME trace as the API span it continues, "
        "not start a disconnected one"
    )


def test_continue_trace_without_a_carrier_starts_a_fresh_root_span(exporter):
    """A task enqueued before trace propagation existed, or with tracing turned off at
    enqueue time, has no trace_context -- continue_trace must still work, just as an
    unlinked root span, not raise."""
    with continue_trace(None, span_name="worker.process_task:legacy", tracer_name="worker"):
        pass

    spans = exporter.get_finished_spans()
    assert any(s.name == "worker.process_task:legacy" for s in spans)


def test_two_unrelated_enqueues_produce_two_different_trace_ids(exporter):
    """Sanity check the other direction: continue_trace isn't accidentally merging every
    task into one trace regardless of its carrier."""
    tracer = otel_trace.get_tracer("test.api")

    with tracer.start_as_current_span("api.enqueue_a") as span_a:
        carrier_a = inject_trace_context({})
        trace_id_a = span_a.get_span_context().trace_id
    with tracer.start_as_current_span("api.enqueue_b") as span_b:
        carrier_b = inject_trace_context({})
        trace_id_b = span_b.get_span_context().trace_id

    assert trace_id_a != trace_id_b

    with continue_trace(carrier_a, span_name="worker.a", tracer_name="worker") as worker_span_a:
        worker_trace_id_a = worker_span_a.get_span_context().trace_id
    with continue_trace(carrier_b, span_name="worker.b", tracer_name="worker") as worker_span_b:
        worker_trace_id_b = worker_span_b.get_span_context().trace_id

    assert worker_trace_id_a == trace_id_a
    assert worker_trace_id_b == trace_id_b
