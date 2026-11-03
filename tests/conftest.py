"""Shared pytest fixtures.

Database-backed tests run against the local Postgres container (see docker-compose.yml).
Every fixture-created tenant is purged afterwards so tests leave no rows behind.
"""

from typing import Iterator

import pytest
from starlette.testclient import TestClient

from apps.api.main import app
from tests.support import Tenant, create_tenant, purge_organization


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
