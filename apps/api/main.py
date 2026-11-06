"""FastAPI application for Tattva AI Film Director.

Run with: ``uvicorn apps.api.main:app --reload``
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.errors import register_exception_handlers
from apps.api.routers import (
    approvals,
    assets,
    auth,
    film_bible,
    health,
    journey,
    projects,
    research,
    storyboard,
    workflows,
)
from packages.core.config import Settings, get_settings
from packages.core.logging import configure_logging
from packages.workflows.checkpointer import setup_checkpointer_schema


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Checkpoint DDL must run before any request opens a transaction (see checkpointer.py).
    setup_checkpointer_schema()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Tattva AI Film Director API",
        version="1.0.0",
        description="Tenant-scoped API for projects, assets, Script Intelligence workflows, "
        "human approval gates, canonical versions and audit trails.",
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Actor-ID", "Authorization"],
    )
    register_exception_handlers(app)

    app.include_router(health.router)
    for module in (projects, assets, workflows, approvals, research, storyboard, film_bible, journey):
        app.include_router(module.router, prefix=settings.api_v1_str)

    # Dev-only login: never registered outside local development (ADR-003). In every
    # other environment this path simply does not exist and 404s.
    if settings.environment == "development":
        app.include_router(auth.router, prefix=settings.api_v1_str)
    return app


app = create_app()
