"""Unit tests for packages.services.auth: direct provider verification logic.

test_authentication.py covers the HTTP-layer (get_actor, dev-login) behaviour; this file
covers the cryptographic correctness of each AuthProvider in isolation, including the
OIDC/JWKS success path that never otherwise gets exercised (no real IdP is configured
anywhere in this repository yet).
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from packages.services.auth import (
    AuthConfigurationError,
    AuthenticationError,
    DevTokenAuthProvider,
    OIDCAuthProvider,
)


def test_dev_provider_requires_a_secret_key():
    with pytest.raises(AuthConfigurationError):
        DevTokenAuthProvider("", 3600)


def test_dev_provider_round_trips_issue_and_verify():
    provider = DevTokenAuthProvider("a-sufficiently-long-test-secret-key-value!!", 3600)
    token = provider.issue(subject="user-123")
    principal = provider.verify_token(token)
    assert principal.subject == "user-123"
    assert principal.issuer == "tattva-dev"


def test_dev_provider_rejects_tokens_from_a_different_issuer():
    secret = "a-sufficiently-long-test-secret-key-value!!"
    provider = DevTokenAuthProvider(secret, 3600)
    foreign = jwt.encode(
        {"sub": "x", "iss": "someone-else", "iat": int(time.time()), "exp": int(time.time()) + 60},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        provider.verify_token(foreign)


class _FakeJWKClient:
    """Stands in for jwt.PyJWKClient without any network access."""

    def __init__(self, signing_key):
        self._signing_key = signing_key

    def get_signing_key_from_jwt(self, token):
        return self._signing_key


def _build_oidc_provider(monkeypatch, public_key, *, issuer: str, audience: str):
    provider = OIDCAuthProvider(issuer=issuer, jwks_url="https://idp.example.com/jwks.json", audience=audience)
    monkeypatch.setattr(provider, "_jwk_client", _FakeJWKClient(signing_key=type("K", (), {"key": public_key})()))
    return provider


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def test_oidc_requires_full_configuration():
    with pytest.raises(AuthConfigurationError):
        OIDCAuthProvider(issuer="", jwks_url="", audience="")
    with pytest.raises(AuthConfigurationError):
        OIDCAuthProvider(issuer="https://idp.example.com/", jwks_url="", audience="tattva-api")


def test_oidc_provider_verifies_a_genuinely_signed_token(monkeypatch, rsa_keypair):
    private_key, public_key = rsa_keypair
    provider = _build_oidc_provider(
        monkeypatch, public_key, issuer="https://idp.example.com/", audience="tattva-api"
    )
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "oidc|abc123",
            "iss": "https://idp.example.com/",
            "aud": "tattva-api",
            "iat": now,
            "exp": now + 300,
            "email_verified": True,
        },
        private_key,
        algorithm="RS256",
    )

    principal = provider.verify_token(token)

    assert principal.subject == "oidc|abc123"
    assert principal.issuer == "https://idp.example.com/"


def test_oidc_provider_rejects_unverified_email(monkeypatch, rsa_keypair):
    private_key, public_key = rsa_keypair
    provider = _build_oidc_provider(
        monkeypatch, public_key, issuer="https://idp.example.com/", audience="tattva-api"
    )
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "oidc|abc123",
            "iss": "https://idp.example.com/",
            "aud": "tattva-api",
            "iat": now,
            "exp": now + 300,
            "email_verified": False,
        },
        private_key,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        provider.verify_token(token)


def test_oidc_provider_rejects_wrong_audience(monkeypatch, rsa_keypair):
    private_key, public_key = rsa_keypair
    provider = _build_oidc_provider(
        monkeypatch, public_key, issuer="https://idp.example.com/", audience="tattva-api"
    )
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "oidc|abc123",
            "iss": "https://idp.example.com/",
            "aud": "someone-elses-api",
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        provider.verify_token(token)


def test_oidc_provider_rejects_token_signed_by_a_different_key(monkeypatch, rsa_keypair):
    _, public_key = rsa_keypair
    other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    provider = _build_oidc_provider(
        monkeypatch, public_key, issuer="https://idp.example.com/", audience="tattva-api"
    )
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "oidc|abc123",
            "iss": "https://idp.example.com/",
            "aud": "tattva-api",
            "iat": now,
            "exp": now + 300,
        },
        other_private_key,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        provider.verify_token(token)
