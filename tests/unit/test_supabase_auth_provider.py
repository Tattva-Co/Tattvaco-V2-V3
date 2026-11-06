"""SupabaseAuthProvider (DEC-002: Supabase Auth chosen 2026-11-06).

Tokens are signed locally with throwaway keys shaped like Supabase's asymmetric signing
keys (ES256 by default, RS256 also supported); the JWKS fetch is replaced so no network
is used.
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from packages.core.config import Settings
from packages.services.auth import (
    AuthConfigurationError,
    AuthenticationError,
    SupabaseAuthProvider,
    build_auth_provider,
)

URL = "https://abcdefghijklmnop.supabase.co"
ISSUER = f"{URL}/auth/v1"


class _FakeJWKClient:
    def __init__(self, public_key):
        self._key = type("K", (), {"key": public_key})()

    def get_signing_key_from_jwt(self, token):
        return self._key


def _provider(monkeypatch, public_key) -> SupabaseAuthProvider:
    provider = SupabaseAuthProvider(URL)
    monkeypatch.setattr(provider, "_jwk_client", _FakeJWKClient(public_key))
    return provider


def _claims(**overrides) -> dict:
    now = int(time.time())
    claims = {
        "sub": "8f9c2a4e-1b2c-4d5e-8f90-123456789abc",
        "iss": ISSUER,
        "aud": "authenticated",
        "role": "authenticated",
        "is_anonymous": False,
        "email": "director@example.com",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def ec_keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


def test_derives_issuer_jwks_and_audience_from_the_project_url():
    provider = SupabaseAuthProvider(URL + "/")
    assert provider._issuer == ISSUER
    assert provider._audience == "authenticated"
    assert provider._jwk_client.uri == f"{ISSUER}/.well-known/jwks.json"


@pytest.mark.parametrize("url", ["", "   ", "http://abcdefghijklmnop.supabase.co"])
def test_requires_an_https_project_url(url):
    with pytest.raises(AuthConfigurationError):
        SupabaseAuthProvider(url)


def test_accepts_an_es256_signed_user_token(monkeypatch, ec_keypair):
    private_key, public_key = ec_keypair
    token = jwt.encode(_claims(), private_key, algorithm="ES256")
    principal = _provider(monkeypatch, public_key).verify_token(token)
    assert principal.subject == "8f9c2a4e-1b2c-4d5e-8f90-123456789abc"
    assert principal.issuer == ISSUER


def test_accepts_an_rs256_signed_user_token(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(_claims(), private_key, algorithm="RS256")
    assert _provider(monkeypatch, private_key.public_key()).verify_token(token).issuer == ISSUER


@pytest.mark.parametrize(
    "overrides",
    [
        {"role": "anon"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"aud": "something-else"},
        {"iss": "https://other-project.supabase.co/auth/v1"},
        {"exp": int(time.time()) - 3600},
    ],
)
def test_rejects_tokens_that_are_not_a_signed_in_users(monkeypatch, ec_keypair, overrides):
    private_key, public_key = ec_keypair
    token = jwt.encode(_claims(**overrides), private_key, algorithm="ES256")
    with pytest.raises(AuthenticationError):
        _provider(monkeypatch, public_key).verify_token(token)


def test_rejects_legacy_hs256_tokens(monkeypatch, ec_keypair):
    _, public_key = ec_keypair
    token = jwt.encode(_claims(), "legacy-shared-jwt-secret-at-least-32-bytes!!", algorithm="HS256")
    with pytest.raises(AuthenticationError):
        _provider(monkeypatch, public_key).verify_token(token)


def test_rejects_a_token_signed_by_a_different_key(monkeypatch, ec_keypair):
    _, public_key = ec_keypair
    stranger = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(_claims(), stranger, algorithm="ES256")
    with pytest.raises(AuthenticationError):
        _provider(monkeypatch, public_key).verify_token(token)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_factory_selects_supabase_by_default_in_staging_and_production(environment):
    provider = build_auth_provider(Settings(environment=environment, supabase_url=URL))
    assert isinstance(provider, SupabaseAuthProvider)


def test_factory_fails_closed_without_a_supabase_url():
    with pytest.raises(AuthConfigurationError):
        build_auth_provider(Settings(environment="production", supabase_url=""))
