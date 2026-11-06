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

    # Object storage
    storage_provider: Literal["local"] = "local"
    storage_local_root: str = "./data/storage"
    storage_max_upload_bytes: int = 100 * 1024 * 1024
    storage_allowed_mime_types: CommaList = Field(
        default_factory=lambda: [
            "text/plain",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/json",
        ]
    )

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
    #   - "staging"/"production": a token issued by an external OIDC provider (RS256,
    #     verified against oidc_jwks_url). Until oidc_issuer/oidc_jwks_url/oidc_audience
    #     are configured, every request in those environments fails closed with a 500
    #     (server misconfigured) rather than silently accepting unverified identity.
    secret_key: str = ""
    access_token_ttl_seconds: int = 3600

    # Idempotency-Key (TFD-OPS-004): how long a stored response can be replayed.
    idempotency_ttl_hours: int = 24
    oidc_issuer: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = ""

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
