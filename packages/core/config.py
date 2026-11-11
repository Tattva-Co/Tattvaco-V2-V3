"""Typed application settings — the single place environment variables are read.

Values come from process environment variables, then a local ``.env`` file, then the
defaults below (which target the docker-compose development stack). Every process
(API, worker, UI) calls :func:`get_settings`; nothing else should call ``os.getenv``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated

CommaList = Annotated[List[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: str = "INFO"
    debug: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_v1_str: str = "/api/v1"
    cors_allow_origins: CommaList = Field(default_factory=lambda: ["http://localhost:8501"])

    # Streamlit UI
    streamlit_api_base_url: str = "http://localhost:8000/api/v1"
    ui_request_timeout_seconds: float = 30.0

    # Canonical database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:55432/tattva_film_director"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # LangGraph checkpointer (defaults to the canonical database)
    checkpoint_database_url: str | None = None

    # Object storage (C7). "s3" speaks the S3 API, so it works against real AWS S3 or any
    # S3-compatible endpoint (set storage_s3_endpoint_url) -- see docs/audit/10 DEC-034 for
    # why this isn't paired with a MinIO docker-compose service (MinIO retired its free
    # Docker Hub/Quay images in Sept 2026; the adapter is tested against a `moto` mock
    # instead, which needs no container at all).
    storage_provider: Literal["local", "s3"] = "local"
    storage_local_root: str = "./data/storage"
    storage_max_upload_bytes: int = 100 * 1024 * 1024
    storage_stream_chunk_bytes: int = 1024 * 1024
    storage_allowed_mime_types: CommaList = Field(
        default_factory=lambda: [
            "text/plain",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/json",
            "application/x-final-draft",
        ]
    )
    storage_s3_bucket: str = ""
    storage_s3_region: str = "us-east-1"
    # Empty uses the real AWS endpoint; set to a non-AWS S3-compatible provider's URL
    # (Cloudflare R2, Backblaze B2, a self-hosted MinIO/Garage) to point elsewhere.
    storage_s3_endpoint_url: str = ""
    storage_s3_access_key_id: str = ""
    storage_s3_secret_access_key: str = ""

    # Malware scanning (C7). "noop" always reports clean -- a labelled stub seam for a
    # real scanner (e.g. ClamAV) later; see packages/services/scanning.py.
    malware_scanner_provider: Literal["noop"] = "noop"

    # Worker (C6: lease/retry/dead-letter, docs/audit/08 PERF-04)
    worker_poll_interval_seconds: float = 1.0
    worker_id: str = "worker-1"
    worker_lease_seconds: int = 300  # how long a claim is honored before being reclaimable
    worker_max_attempts: int = 5
    worker_backoff_base_seconds: float = 10.0  # exponential backoff base; jitter added on top
    worker_backoff_max_seconds: float = 900.0  # cap a single retry delay at 15 minutes

    # Authentication (ADR-003). In "test", callers identify via the X-Actor-ID header
    # (no token required). In every other environment, callers must present a signed
    # Bearer access token:
    #   - "development": a token issued by this process itself (HS256, signed with
    #     secret_key) via POST /api/v1/auth/dev-login. No external identity provider.
    #   - "staging"/"production": a token from the external identity provider chosen by
    #     auth_provider. DEC-002 chose Supabase Auth (2026-11-06): set supabase_url and
    #     the issuer, JWKS URL and audience are derived from it. "oidc" keeps the
    #     vendor-neutral path (oidc_issuer/oidc_jwks_url/oidc_audience). Until the chosen
    #     provider is configured, every request in those environments fails closed with
    #     a 500 (server misconfigured) rather than accepting unverified identity.
    secret_key: str = ""
    access_token_ttl_seconds: int = 3600
    auth_provider: Literal["supabase", "oidc"] = "supabase"
    supabase_url: str = ""  # e.g. https://<project-ref>.supabase.co
    oidc_issuer: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = ""

    # Idempotency-Key (TFD-OPS-004): how long a stored response can be replayed.
    idempotency_ttl_hours: int = 24

    # Reserved for upcoming provider adapters (see docs/implementation/OPEN_DECISIONS.md).
    # Declared so they are validated and documented; not yet consumed by any code path.
    model_gateway_provider: Literal["mock"] = "mock"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    higgsfield_integration_mode: Literal["manual_export"] = "manual_export"
    higgsfield_api_base_url: str = "https://api.higgsfield.ai"
    higgsfield_api_key: str = ""

    @field_validator("cors_allow_origins", "storage_allowed_mime_types", mode="before")
    @classmethod
    def _split_comma_list(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def checkpoint_conn_str(self) -> str:
        """psycopg3 connection string for the LangGraph PostgresSaver."""
        url = self.checkpoint_database_url or self.database_url
        return url.replace("postgresql+psycopg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
