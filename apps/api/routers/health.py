"""Liveness/readiness."""

from datetime import datetime, timezone

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
    return HealthResponse(status="ok", service="tattva-api", timestamp=datetime.now(timezone.utc))
