"""Authentication (ADR-003, approval gate 1, docs/audit/08 SEC-01/SEC-02).

The "test" environment keeps the X-Actor-ID header shortcut (exercised by every other
test file via tests.support.as_actor). This file exercises the real token paths that
every OTHER environment must use: development's self-issued dev tokens, and the
fail-closed behaviour when OIDC is required but not configured.

Each test builds its own app instance (via create_app + dependency_overrides) rather
than importing the module-level `app` singleton, because route registration for
/auth/dev-login happens once at app construction time based on `environment`.
"""

from __future__ import annotations

import time

import jwt
import pytest
from starlette.testclient import TestClient

from apps.api.dependencies import get_settings
from apps.api.main import create_app
from packages.core.config import Settings
from tests.support import create_tenant, purge_organization


def _app_for(**overrides) -> tuple[TestClient, Settings]:
    settings = Settings(**overrides)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    # raise_server_exceptions=False: we assert on the JSON error body a real deployment
    # would return. Starlette's TestClient otherwise re-raises any exception caught only
    # by the generic Exception/500 handler (ServerErrorMiddleware does this by design,
    # "to allow test clients to optionally raise the error") even though a 500 response
    # was correctly produced and sent.
    return TestClient(app, raise_server_exceptions=False), settings


def test_dev_login_issues_a_usable_bearer_token():
    client, _ = _app_for(environment="development", secret_key="unit-test-secret-at-least-32-bytes-long!!")
    tenant = create_tenant()
    try:
        resp = client.post("/api/v1/auth/dev-login", json={"email": "someone@example.com"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["user_id"]
        assert body["organization_id"]

        authed = client.get(
            "/api/v1/projects", headers={"Authorization": f"Bearer {body['access_token']}"}
        )
        assert authed.status_code == 200, authed.text
    finally:
        purge_organization(tenant.org_id)


def test_dev_login_route_does_not_exist_outside_development():
    client, _ = _app_for(environment="test")
    resp = client.post("/api/v1/auth/dev-login", json={"email": "someone@example.com"})
    assert resp.status_code == 404


def test_development_requires_a_token_no_fallback_identity():
    """Replaces the removed get_or_create_default_actor fallback (SEC-02)."""
    client, _ = _app_for(environment="development", secret_key="unit-test-secret-at-least-32-bytes-long!!")
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 401
    assert resp.json()["error"] == "AuthenticationError"

    # An X-Actor-ID header alone (no Bearer token) must not authenticate outside test.
    resp = client.get("/api/v1/projects", headers={"X-Actor-ID": "anything"})
    assert resp.status_code == 401


def test_development_rejects_expired_token():
    client, settings = _app_for(environment="development", secret_key="unit-test-secret-at-least-32-bytes-long!!")
    expired = jwt.encode(
        {"sub": "whoever", "iss": "tattva-dev", "iat": int(time.time()) - 120, "exp": int(time.time()) - 60},
        settings.secret_key,
        algorithm="HS256",
    )
    resp = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_development_rejects_token_signed_with_wrong_secret():
    client, _ = _app_for(environment="development", secret_key="the-real-secret-at-least-32-bytes-long!!")
    forged = jwt.encode(
        {"sub": "whoever", "iss": "tattva-dev", "iat": int(time.time()), "exp": int(time.time()) + 60},
        "an-attackers-completely-wrong-guess-32-bytes!!",
        algorithm="HS256",
    )
    resp = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


def test_development_rejects_token_for_unknown_user():
    client, settings = _app_for(environment="development", secret_key="unit-test-secret-at-least-32-bytes-long!!")
    token = jwt.encode(
        {"sub": "not-a-real-user-id", "iss": "tattva-dev", "iat": int(time.time()), "exp": int(time.time()) + 60},
        settings.secret_key,
        algorithm="HS256",
    )
    resp = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "AuthenticationError"


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_requests_fail_closed_when_auth_is_not_configured(environment):
    """No SECRET_KEY (dev) or no OIDC settings (staging/prod) must never admit a caller."""
    client, _ = _app_for(environment=environment)  # no secret_key, no oidc_* set
    resp = client.get("/api/v1/projects", headers={"Authorization": "Bearer whatever"})
    assert resp.status_code == 500, resp.text
    assert resp.json()["error"] == "InternalError"


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_dev_tokens_are_not_accepted_in_staging_or_production(environment):
    """A dev-issued token must not work once OIDC is configured for staging/production."""
    client, settings = _app_for(
        environment=environment,
        oidc_issuer="https://idp.example.com/",
        oidc_jwks_url="https://idp.example.com/.well-known/jwks.json",
        oidc_audience="tattva-api",
    )
    dev_token = jwt.encode(
        {"sub": "someone", "iss": "tattva-dev", "iat": int(time.time()), "exp": int(time.time()) + 60},
        "whatever-secret-but-at-least-32-bytes-long!!",
        algorithm="HS256",
    )
    resp = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {dev_token}"})
    assert resp.status_code == 401
