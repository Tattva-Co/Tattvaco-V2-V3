"""LangGraph PostgreSQL Checkpointer initialization and lifecycle management."""

import os
from typing import Generator
from contextlib import contextmanager
from langgraph.checkpoint.postgres import PostgresSaver

DEFAULT_CONN_STR = "postgresql://postgres:postgres@localhost:55432/tattva_film_director"
CHECKPOINT_CONN_STR = os.getenv("CHECKPOINT_DATABASE_URL", os.getenv("DATABASE_URL", DEFAULT_CONN_STR))

# Ensure standard postgresql:// prefix instead of postgresql+psycopg:// for psycopg3
if CHECKPOINT_CONN_STR.startswith("postgresql+psycopg://"):
    CHECKPOINT_CONN_STR = CHECKPOINT_CONN_STR.replace("postgresql+psycopg://", "postgresql://", 1)


@contextmanager
def get_checkpointer() -> Generator[PostgresSaver, None, None]:
    """Yield an initialized PostgresSaver checkpointer instance."""
    with PostgresSaver.from_conn_string(CHECKPOINT_CONN_STR) as saver:
        saver.setup()
        yield saver
