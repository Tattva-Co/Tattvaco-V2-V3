"""Storyboard endpoints (canonical panels)."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import StoryboardPanelResponse
from packages.services.identity import ActorContext
from packages.services.storyboard import StoryboardService

router = APIRouter(prefix="/projects/{project_id}/storyboard", tags=["storyboard"])


@router.get("/panels", response_model=List[StoryboardPanelResponse])
def list_panels(
    project_id: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return StoryboardService(db).list_panels(actor, project_id)

