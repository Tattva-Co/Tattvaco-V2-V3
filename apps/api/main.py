"""FastAPI application for Tattva AI Film Director.

Run with: ``uvicorn apps.api.main:app --reload``
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.errors import register_exception_handlers
from apps.api.routers import approvals, assets, health, projects, research, storyboard, workflows
from packages.core.config import Settings, get_settings
from packages.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Tattva AI Film Director API",
        version="1.0.0",
        description="Tenant-scoped API for projects, assets, Script Intelligence workflows, "
        "human approval gates, canonical versions and audit trails.",
        debug=settings.debug,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Actor-ID"],
    )
    register_exception_handlers(app)

    app.include_router(health.router)
    for module in (projects, assets, workflows, approvals, research, storyboard):
        app.include_router(module.router, prefix=settings.api_v1_str)
    return app


app = create_app()
