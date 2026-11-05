"""FastAPI dependency providers: settings, DB session, storage, actor identity."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from packages.core.config import Settings, get_settings
from packages.persistence.database import get_db
from packages.services.auth import AuthProvider, DevTokenAuthProvider, build_auth_provider
from packages.services.identity import ActorContext, AuthenticationError, IdentityService
from packages.storage.factory import get_storage
from packages.storage.service import StorageService

__all__ = ["get_db", "get_settings", "get_storage", "get_actor", "Settings", "StorageService"]


@lru_cache
def _auth_provider_for(
    environment: str, secret_key: str, access_token_ttl_seconds: int, jwks_url: str, issuer: str, audience: str
) -> AuthProvider:
    # Cached on the handful of plain hashable values that determine the provider's
    # identity — not on the Settings object (pydantic-settings leaves it unhashable, and
    # test fixtures freely substitute new instances via app.dependency_overrides, as
    # test_assets_api.py does). This matters for OIDCAuthProvider: its PyJWKClient caches
    # fetched signing keys across calls on the SAME instance, so a distinct, stable
    # configuration gets one long-lived provider instead of refetching JWKS per request.
    settings = Settings(
        environment=environment,  # type: ignore[arg-type]
        secret_key=secret_key,
        access_token_ttl_seconds=access_token_ttl_seconds,
        oidc_jwks_url=jwks_url,
        oidc_issuer=issuer,
        oidc_audience=audience,
    )
    return build_auth_provider(settings)


def _get_auth_provider(settings: Settings) -> AuthProvider:
    return _auth_provider_for(
        settings.environment,
        settings.secret_key,
        settings.access_token_ttl_seconds,
        settings.oidc_jwks_url,
        settings.oidc_issuer,
        settings.oidc_audience,
    )


def get_actor(
    authorization: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ActorContext:
    """Resolve the verified caller identity for this request (ADR-003).

    - ``environment == "test"``: the ``X-Actor-ID`` header names an existing user
      directly (no token). A Bearer token is also accepted here so the authentication
      test suite can exercise the real token path without external IdP infrastructure.
    - every other environment: a Bearer token is required and verified by this
      environment's :class:`~packages.services.auth.AuthProvider` (dev-issued HS256 in
      development, OIDC/JWKS RS256 in staging/production). There is no fallback identity.
    """
    identity = IdentityService(db)

    if settings.environment == "test":
        if authorization:
            provider: AuthProvider = DevTokenAuthProvider(
                settings.secret_key or "test-only-secret", settings.access_token_ttl_seconds
            )
            principal = provider.verify_token(_bearer_token(authorization))
            return identity.resolve_principal(principal)
        return identity.resolve_header(x_actor_id)

    principal = _get_auth_provider(settings).verify_token(_bearer_token(authorization))
    return identity.resolve_principal(principal)


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AuthenticationError("Missing or malformed Authorization header.")
    return token
