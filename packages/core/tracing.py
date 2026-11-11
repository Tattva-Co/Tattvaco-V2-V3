"""OpenTelemetry tracing (C9): one trace spans API -> outbox -> worker -> graph.

No tracing backend is wired up in this repo -- spans export to the console by default
(`ConsoleSpanExporter`), which is enough to see real trace/span IDs locally and is what
`tests/unit/test_tracing.py` asserts against via an in-memory exporter. Setting
`otel_exporter_otlp_endpoint` switches to a real OTLP HTTP exporter (Tempo, Honeycomb,
Jaeger, any OTLP-compatible collector) with no other code change.

The one non-obvious piece: a span started while handling an HTTP request (enqueuing a
workflow run) and a span started later in a completely different process (the worker,
polling the same outbox row) are made part of the SAME trace by propagating the W3C
`traceparent` through the one channel that already crosses that boundary -- the outbox
task's own `payload` JSON column (packages/services/{script_intelligence,
historical_research,storyboard,film_bible}.py write it when enqueuing;
apps/worker/worker.py reads it back when claiming).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Span, Tracer

from packages.core.config import Settings

_configured = False


def configure_tracing(settings: Settings) -> None:
    """Set the global TracerProvider once per process. Safe to call repeatedly (a
    second call is a no-op) -- apps/api/main.py and apps/worker/worker.py each call this
    independently, since they are separate processes."""
    global _configured
    if _configured or not settings.otel_enabled:
        return
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.otel_service_name}))
    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        # Batched: a real backend over the network should not add per-request latency,
        # and occasional network hiccups should not block request handling.
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
        )
    else:
        # Synchronous, not batched: a stdout write is effectively free, and this sidesteps
        # BatchSpanProcessor's background export thread occasionally losing its race with
        # process shutdown (a cosmetic "I/O operation on closed file" at interpreter exit,
        # harmless but noisy -- most visible under pytest, which closes its captured
        # stdout before every daemon thread is guaranteed to have stopped).
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer(name: str) -> Tracer:
    return trace.get_tracer(f"tattva.{name}")


def inject_trace_context(carrier: dict[str, Any]) -> dict[str, Any]:
    """Capture the current span's trace context into a plain dict -- call this right
    before persisting something (here, an outbox task's payload) that a later process
    will read back and should be considered part of the same trace."""
    inject(carrier)
    return carrier


@contextmanager
def continue_trace(carrier: dict[str, Any] | None, span_name: str, tracer_name: str) -> Generator[Span]:
    """Start a span as a child of whatever trace context `carrier` holds (from
    `inject_trace_context`), or as a fresh root span if there is none (e.g. a task
    enqueued before this migration, or tracing disabled when it was created)."""
    context = extract(carrier or {})
    tracer = get_tracer(tracer_name)
    with tracer.start_as_current_span(span_name, context=context) as span:
        yield span
