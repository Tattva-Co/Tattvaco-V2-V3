"""Process-wide logging configuration shared by the API, worker and UI."""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once per process. Safe to call repeatedly."""
    global _configured
    if _configured:
        return
    logging.basicConfig(level=level.upper(), format=_LOG_FORMAT)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"tattva.{name}")
