"""FastAPI dependency providers: settings, DB session, storage, actor identity."""

from typing import Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from packages.core.config import Settings, get_settings
from packages.persistence.database import get_db
from packages.services.identity import ActorContext, IdentityService
from packages.storage.factory import get_storage
from packages.storage.service import StorageService

__all__ = ["get_db", "get_settings", "get_storage", "get_actor", "Settings", "StorageService"]

DEV_FALLBACK_ENVIRONMENTS = {"development", "test"}


def get_actor(
    x_actor_id: Optional[str] = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ActorContext:
    return IdentityService(db).resolve(
        x_actor_id,
        allow_dev_fallback=settings.environment in DEV_FALLBACK_ENVIRONMENTS,
    )
