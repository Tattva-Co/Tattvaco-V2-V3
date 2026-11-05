"""Shared pytest fixtures.

Tests NEVER touch the development database (DEC-015). Before any application module is
imported, this file:

1. points ``DATABASE_URL`` at a dedicated test database (``<dev db name>_test`` on the same
   server, or ``TATTVA_TEST_DATABASE_URL`` when set, e.g. in CI);
2. creates that database if it does not exist and migrates it to Alembic head;
3. points asset storage at a throwaway directory;
4. sets ``ENVIRONMENT=test``.

Settings are cached at import time (``get_settings`` is ``lru_cache``-d and the engine is
created on import), so this must run before ``apps``/``packages`` are imported.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from typing import Iterator

from sqlalchemy.engine import make_url

_DEV_DEFAULT_URL = "postgresql+psycopg://postgres:postgres@localhost:55432/tattva_film_director"


def _test_database_url() -> str:
    explicit = os.environ.get("TATTVA_TEST_DATABASE_URL")
    if explicit:
        return explicit
    base = make_url(os.environ.get("DATABASE_URL", _DEV_DEFAULT_URL))
    name = base.database or "tattva_film_director"
    if not name.endswith("_test"):
        name = f"{name}_test"
    return base.set(database=name).render_as_string(hide_password=False)


def _ensure_database(url: str) -> None:
    import psycopg

    target = make_url(url)
    admin = target.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    with psycopg.connect(admin, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (target.database,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{target.database}"')


_TEST_DB_URL = _test_database_url()
os.environ["DATABASE_URL"] = _TEST_DB_URL
os.environ.pop("CHECKPOINT_DATABASE_URL", None)  # checkpoints live in the test DB too
os.environ["ENVIRONMENT"] = "test"
_STORAGE_ROOT = tempfile.mkdtemp(prefix="tattva-test-storage-")
os.environ["STORAGE_LOCAL_ROOT"] = _STORAGE_ROOT
atexit.register(shutil.rmtree, _STORAGE_ROOT, ignore_errors=True)

_ensure_database(_TEST_DB_URL)


def _migrate_to_head() -> None:
    from alembic import command
    from alembic.config import Config

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(repo_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(repo_root, "packages/persistence/migrations"))
    command.upgrade(cfg, "head")


_migrate_to_head()

from packages.workflows.checkpointer import setup_checkpointer_schema  # noqa: E402

setup_checkpointer_schema()

import pytest  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from apps.api.main import app  # noqa: E402
from packages.persistence.database import DATABASE_URL  # noqa: E402
from tests.support import Tenant, create_tenant, purge_organization  # noqa: E402

assert make_url(DATABASE_URL).database == make_url(_TEST_DB_URL).database, (
    "Refusing to run tests: the application engine is not bound to the test database."
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def tenant() -> Iterator[Tenant]:
    t = create_tenant()
    yield t
    purge_organization(t.org_id)


@pytest.fixture
def other_tenant() -> Iterator[Tenant]:
    t = create_tenant()
    yield t
    purge_organization(t.org_id)
