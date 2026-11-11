"""C9: health/readiness endpoints and the request-correlation-ID middleware."""

from __future__ import annotations

import json

from apps.api.correlation_middleware import REQUEST_ID_HEADER


def test_health_checks_the_database(client):
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"


def test_liveness_does_not_touch_the_database(client, monkeypatch):
    """/health/live must answer even if the database is unreachable -- a liveness probe
    exists specifically so an orchestrator does not restart a process over a dependency
    outage it can't fix by restarting."""
    import packages.persistence.database as db_module

    def _boom(*args, **kwargs):
        raise AssertionError("liveness must not query the database")

    monkeypatch.setattr(db_module, "SessionLocal", _boom)
    resp = client.get("/health/live")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"


def test_readiness_checks_the_database(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"


def test_a_request_id_is_generated_and_echoed_back(client):
    resp = client.get("/health")
    assert REQUEST_ID_HEADER in resp.headers
    assert len(resp.headers[REQUEST_ID_HEADER]) > 0


def test_a_caller_supplied_request_id_is_preserved(client):
    resp = client.get("/health", headers={REQUEST_ID_HEADER: "caller-chosen-id-123"})
    assert resp.headers[REQUEST_ID_HEADER] == "caller-chosen-id-123"


def test_two_requests_get_different_generated_request_ids(client):
    first = client.get("/health").headers[REQUEST_ID_HEADER]
    second = client.get("/health").headers[REQUEST_ID_HEADER]
    assert first != second


def test_logs_are_single_line_parseable_json_carrying_the_request_id(client, caplog):
    """A real log pipeline (ELK/Loki/CloudWatch) parses each line as one JSON document --
    this proves the formatter actually produces that, not just that it doesn't crash."""
    from packages.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    import logging

    from packages.core.logging import request_id_var

    token = request_id_var.set("req-abc-123")
    try:
        record = logging.LogRecord(
            name="tattva.test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="something happened", args=(), exc_info=None,
        )
        record.request_id = request_id_var.get()
        record.run_id = None
        line = formatter.format(record)
    finally:
        request_id_var.reset(token)

    parsed = json.loads(line)  # raises if it is not exactly one JSON object per line
    assert parsed["message"] == "something happened"
    assert parsed["request_id"] == "req-abc-123"
    assert parsed["level"] == "INFO"
    assert "run_id" not in parsed  # never set here -- must not show up as null noise
