"""LangGraph PostgreSQL Checkpointer initialization and lifecycle management."""

from contextlib import contextmanager
from typing import Generator

from langgraph.checkpoint.postgres import PostgresSaver

from packages.core.config import get_settings


@contextmanager
def get_checkpointer() -> Generator[PostgresSaver, None, None]:
    """Yield an initialized PostgresSaver checkpointer instance."""
    with PostgresSaver.from_conn_string(get_settings().checkpoint_conn_str) as saver:
        saver.setup()
        yield saver
