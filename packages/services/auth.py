"""Token verification (ADR-003): the ``AuthProvider`` port and its two implementations.

This module answers one question only: *is this bearer token a validly signed,
unexpired credential, and if so, who does it say the caller is?* It never touches the
database and never decides whether that caller is allowed to do anything — that is
``IdentityService`` (maps a verified principal to a ``users`` row) and, from milestone
C4 onward, the authorization/capability layer.

Implementations (``docs/audit/11_APPROVAL_GATE_DECISIONS.md`` gate 1; DEC-002 chose
Supabase Auth on 2026-11-06):

- :class:`DevTokenAuthProvider` is a minimal, self-contained issuer+verifier used only
  in ``environment=development``. It is not an external identity provider; it exists so
  local development and manual testing have a real, signed, expiring token instead of
  trusting a client-supplied header.
- :class:`OIDCAuthProvider` verifies RS256 tokens from a standard OIDC provider via its
  published JWKS. It is vendor-neutral: whichever provider is chosen, it only needs to
  publish ``oidc_issuer``/``oidc_jwks_url``/``oidc_audience``. No request is accepted on
  this path until those settings are configured (fail closed).
- :class:`SupabaseAuthProvider` is the chosen provider for staging and production. It is
  the OIDC verifier pointed at a Supabase project's JWKS, accepting Supabase's asymmetric
  signing keys (ES256, the recommended default, or RS256), plus Supabase-specific claim
  checks. Projects still on the legacy shared HS256 secret publish no public keys and
  must switch to asymmetric signing keys first.
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
    "SupabaseAuthProvider",
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
        self.check_claims(payload)
        return Principal(subject=payload["sub"], issuer=payload["iss"], claims=payload)

    def check_claims(self, payload: dict[str, Any]) -> None:
        """Provider-specific checks after signature, expiry, issuer and audience pass."""


class SupabaseAuthProvider(OIDCAuthProvider):
    """Verifies Supabase Auth access tokens (DEC-002) against the project's JWKS.

    From the project URL ``https://<ref>.supabase.co`` it derives:
    issuer ``<url>/auth/v1``, JWKS ``<url>/auth/v1/.well-known/jwks.json`` and audience
    ``authenticated``. Only tokens for a signed-in, non-anonymous user are accepted.
    """

    ALGORITHMS = ("ES256", "RS256")
    AUDIENCE = "authenticated"

    def __init__(self, supabase_url: str):
        base = supabase_url.strip().rstrip("/")
        if not base:
            raise AuthConfigurationError(
                "Supabase Auth is not configured (supabase_url). Set SUPABASE_URL to the "
                "project URL, e.g. https://<project-ref>.supabase.co; see "
                "docs/audit/11_APPROVAL_GATE_DECISIONS.md gate 1."
            )
        if not base.startswith("https://"):
            raise AuthConfigurationError("supabase_url must be an https:// URL.")
        super().__init__(
            issuer=f"{base}/auth/v1",
            jwks_url=f"{base}/auth/v1/.well-known/jwks.json",
            audience=self.AUDIENCE,
        )

    def check_claims(self, payload: dict[str, Any]) -> None:
        if payload.get("role") != "authenticated":
            raise AuthenticationError("Token is not a signed-in user's access token.")
        if payload.get("is_anonymous") is True:
            raise AuthenticationError("Anonymous Supabase sessions are not accepted.")


def build_auth_provider(settings: Settings) -> AuthProvider:
    """Select the provider for ``settings.environment``. Raises AuthConfigurationError if unready."""
    if settings.environment == "development":
        return DevTokenAuthProvider(settings.secret_key, settings.access_token_ttl_seconds)
    if settings.environment in ("staging", "production"):
        if settings.auth_provider == "supabase":
            return SupabaseAuthProvider(settings.supabase_url)
        return OIDCAuthProvider(settings.oidc_issuer, settings.oidc_jwks_url, settings.oidc_audience)
    raise AuthConfigurationError(
        f"No AuthProvider for environment={settings.environment!r}; "
        "the 'test' environment uses header identity and never calls this factory."
    )
