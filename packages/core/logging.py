"""Process-wide structured logging, shared by the API and worker (C9).

Every log line carries `request_id` (set for the duration of one HTTP request,
apps/api/correlation.py's middleware) and/or `run_id` (set for the duration of one
workflow run's processing -- both while an API handler enqueues/executes it, and while
the worker claims/executes it later). Logging is the simplest possible mechanism to answer
"show me everything that happened for this request/run" across process boundaries without
a tracing backend: `grep '"run_id": "<id>"'` over combined API + worker logs does that
today. The OpenTelemetry tracing in packages/core/tracing.py is the richer, span-based
complement -- the two are not the same mechanism and are not meant to replace each other.
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)

# Every attribute a bare `logging.LogRecord` carries, so the JSON formatter can tell apart
# "a field the standard library always sets" from "an extra field a caller passed via
# logger.info(..., extra={...})", and only emit the latter as additional JSON keys.
_STANDARD_RECORD_ATTRS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
        "relativeCreated", "thread", "threadName", "processName", "process", "message",
        "taskName", "request_id", "run_id",
    }
)


class _CorrelationFilter(logging.Filter):
    """Injects the current request_id/run_id (if either is set) onto every record that
    passes through, so call sites never have to pass them explicitly."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.run_id = run_id_var.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if getattr(record, "request_id", None):
            payload["request_id"] = record.request_id
        if getattr(record, "run_id", None):
            payload["run_id"] = record.run_id
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_") or key in payload:
                continue
            try:
                json.dumps(value)
            except TypeError:
                value = str(value)
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_TEXT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s [req=%(request_id)s run=%(run_id)s]: %(message)s"

_configured = False


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Configure root logging once per process. Safe to call repeatedly."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler()
    handler.addFilter(_CorrelationFilter())
    handler.setFormatter(_JsonFormatter() if json_logs else logging.Formatter(_TEXT_FORMAT))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"tattva.{name}")
