"""Token verification (ADR-003): the ``AuthProvider`` port and its two implementations.

This module answers one question only: *is this bearer token a validly signed,
unexpired credential, and if so, who does it say the caller is?* It never touches the
database and never decides whether that caller is allowed to do anything — that is
``IdentityService`` (maps a verified principal to a ``users`` row) and, from milestone
C4 onward, the authorization/capability layer.

Two implementations exist because no external identity-provider vendor has been chosen
yet (``docs/audit/11_APPROVAL_GATE_DECISIONS.md`` gate 1):

- :class:`DevTokenAuthProvider` is a minimal, self-contained issuer+verifier used only
  in ``environment=development``. It is not an external identity provider; it exists so
  local development and manual testing have a real, signed, expiring token instead of
  trusting a client-supplied header.
- :class:`OIDCAuthProvider` verifies RS256 tokens from a standard OIDC provider via its
  published JWKS. It is vendor-neutral: whichever provider is chosen, it only needs to
  publish ``oidc_issuer``/``oidc_jwks_url``/``oidc_audience``. No request is accepted on
  this path until those settings are configured (fail closed).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import jwt
from jwt import PyJWKClient

from packages.core.config import Settings
from packages.domain.errors import AuthenticationError

__all__ = [
    "AuthenticationError",
    "AuthConfigurationError",
    "Principal",
    "AuthProvider",
    "DevTokenAuthProvider",
    "OIDCAuthProvider",
    "build_auth_provider",
]


class AuthConfigurationError(RuntimeError):
    """The server is not correctly configured to verify tokens in this environment.

    Deliberately NOT a :class:`DomainInvariantError`: this is not the caller's fault and
    must not be reported as a 4xx. It is left unhandled so FastAPI's catch-all maps it to
    a 500, which is logged with a traceback — "fail closed, and say so loudly."
    """


@dataclass(frozen=True)
class Principal:
    """A verified identity, as asserted by a signed token. Not yet a ``users`` row."""

    subject: str  # the token's `sub` claim
    issuer: str  # the token's `iss` claim
    claims: dict[str, Any] = field(default_factory=dict)


class AuthProvider(ABC):
    @abstractmethod
    def verify_token(self, token: str) -> Principal:
        """Verify signature, expiry and issuer/audience. Raise AuthenticationError on failure."""


class DevTokenAuthProvider(AuthProvider):
    """Self-issued HS256 tokens for local development only. Never used in production."""

    ISSUER = "tattva-dev"
    ALGORITHM = "HS256"

    def __init__(self, secret_key: str, ttl_seconds: int):
        if not secret_key:
            raise AuthConfigurationError(
                "SECRET_KEY must be set to a non-empty value to issue or verify dev tokens "
                "(environment=development). Generate one with: python -c "
                "\"import secrets; print(secrets.token_urlsafe(32))\""
            )
        self._secret_key = secret_key
        self._ttl_seconds = ttl_seconds

    def issue(self, subject: str) -> str:
        now = int(time.time())
        payload = {
            "sub": subject,
            "iss": self.ISSUER,
            "iat": now,
            "exp": now + self._ttl_seconds,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self.ALGORITHM)

    def verify_token(self, token: str) -> Principal:
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self.ALGORITHM],
                issuer=self.ISSUER,
                options={"require": ["exp", "iat", "sub", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError(f"Invalid dev token: {exc}") from exc
        return Principal(subject=payload["sub"], issuer=payload["iss"], claims=payload)


class OIDCAuthProvider(AuthProvider):
    """Verifies RS256 access tokens from a standards-compliant OIDC provider via JWKS.

    Vendor-neutral by construction: it only depends on the three published settings, not
    on any provider-specific SDK or endpoint shape (DEC-002 / ADR-003).
    """

    ALGORITHMS = ("RS256",)

    def __init__(self, issuer: str, jwks_url: str, audience: str):
        if not (issuer and jwks_url and audience):
            raise AuthConfigurationError(
                "OIDC is not configured (oidc_issuer/oidc_jwks_url/oidc_audience). "
                "This environment requires a real identity provider; see "
                "docs/ADRs/ADR-003-authentication-and-authorization.md and "
                "docs/audit/11_APPROVAL_GATE_DECISIONS.md gate 1."
            )
        self._issuer = issuer
        self._audience = audience
        # PyJWKClient caches keys and refreshes on an unknown `kid`; one client per
        # process is intentional and matches ADR-003's "cached, refreshed on kid miss".
        # A short, explicit timeout keeps an unreachable IdP from holding a request open
        # for the library's 30s default; callers get a prompt 401/500 instead.
        self._jwk_client = PyJWKClient(jwks_url, timeout=5)

    def verify_token(self, token: str) -> Principal:
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=list(self.ALGORITHMS),
                issuer=self._issuer,
                audience=self._audience,
                leeway=60,
                options={"require": ["exp", "iat", "sub", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError(f"Invalid access token: {exc}") from exc
        if not payload.get("email_verified", True):
            raise AuthenticationError("Identity provider reports an unverified email.")
        return Principal(subject=payload["sub"], issuer=payload["iss"], claims=payload)


def build_auth_provider(settings: Settings) -> AuthProvider:
    """Select the provider for ``settings.environment``. Raises AuthConfigurationError if unready."""
    if settings.environment == "development":
        return DevTokenAuthProvider(settings.secret_key, settings.access_token_ttl_seconds)
    if settings.environment in ("staging", "production"):
        return OIDCAuthProvider(settings.oidc_issuer, settings.oidc_jwks_url, settings.oidc_audience)
    raise AuthConfigurationError(
        f"No AuthProvider for environment={settings.environment!r}; "
        "the 'test' environment uses header identity and never calls this factory."
    )
