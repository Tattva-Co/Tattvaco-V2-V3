"""LangGraph PostgreSQL checkpointer: schema setup and per-invocation access.

Schema setup is deliberately NOT done per invocation. ``PostgresSaver.setup()`` runs
``CREATE INDEX CONCURRENTLY``, which waits for every open transaction on the database to
finish. Called inside a request (while the request's own session is idle in a transaction)
it blocks forever on a fresh database. Setup therefore runs once at process start (API
lifespan, worker start-up, test bootstrap) or as a deploy step:

    python -m packages.workflows.checkpointer
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from langgraph.checkpoint.postgres import PostgresSaver

from packages.core.config import get_settings
from packages.core.logging import get_logger

logger = get_logger("workflows.checkpointer")


def setup_checkpointer_schema() -> None:
    """Create or upgrade the LangGraph-owned checkpoint tables. Idempotent."""
    with PostgresSaver.from_conn_string(get_settings().checkpoint_conn_str) as saver:
        saver.setup()
    logger.info("LangGraph checkpoint schema is ready")


@contextmanager
def get_checkpointer() -> Generator[PostgresSaver, None, None]:
    """Yield a PostgresSaver bound to the checkpoint database (schema must already exist)."""
    with PostgresSaver.from_conn_string(get_settings().checkpoint_conn_str) as saver:
        yield saver


if __name__ == "__main__":
    from packages.core.logging import configure_logging

    configure_logging(get_settings().log_level)
    setup_checkpointer_schema()
