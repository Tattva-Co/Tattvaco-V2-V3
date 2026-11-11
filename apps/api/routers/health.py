"""Liveness/readiness (C9).

/health is kept, unchanged, for anything already calling it (scripts, docs, an external
monitor). /health/live and /health/ready are the two checks a real deployment actually
wants distinguished: a container orchestrator restarts a process that fails liveness
(it's wedged), but only routes traffic away from (without restarting) one that fails
readiness (a dependency, e.g. the database, is temporarily down -- restarting the API
process wouldn't fix that)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    """Healthcheck verifying database connectivity."""
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok", service="tattva-api", timestamp=datetime.now(UTC))


@router.get("/health/live", response_model=HealthResponse)
def live():
    """Liveness: this process is up and able to handle a request at all. No dependency
    (not even the database) is checked -- a database outage must not make an
    orchestrator restart a perfectly healthy API process."""
    return HealthResponse(status="ok", service="tattva-api", timestamp=datetime.now(UTC))


@router.get("/health/ready", response_model=HealthResponse)
def ready(db: Session = Depends(get_db)):
    """Readiness: this instance can actually serve a real request right now."""
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok", service="tattva-api", timestamp=datetime.now(UTC))
