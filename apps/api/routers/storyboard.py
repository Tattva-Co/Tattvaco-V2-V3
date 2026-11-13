"""Storyboard endpoints (canonical panels, PDF/image ingestion, scene mapping)."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    StoryboardIngestRequest,
    StoryboardMappingCreateRequest,
    StoryboardMappingResponse,
    StoryboardPanelResponse,
    WorkflowRunResponse,
)
from packages.services.identity import ActorContext
from packages.services.storyboard import StoryboardService
from packages.services.storyboard_ingestion import StoryboardIngestionService
from packages.storage.factory import get_storage

router = APIRouter(prefix="/projects/{project_id}/storyboard", tags=["storyboard"])


@router.get("/panels", response_model=List[StoryboardPanelResponse])
def list_panels(
    project_id: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return StoryboardService(db).list_panels(actor, project_id)


@router.post("/ingest", response_model=WorkflowRunResponse, status_code=status.HTTP_201_CREATED)
def ingest_pdf(
    project_id: str, req: StoryboardIngestRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return StoryboardIngestionService(db, get_storage()).ingest_pdf(actor, project_id, req.source_asset_id)


@router.get("/mappings", response_model=List[StoryboardMappingResponse])
def list_mappings(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return StoryboardService(db).list_mappings_for_project(actor, project_id)


@router.post("/mappings", response_model=StoryboardMappingResponse, status_code=status.HTTP_201_CREATED)
def create_mapping(
    project_id: str, req: StoryboardMappingCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return StoryboardService(db).map_panel_to_scene(actor, project_id, req.panel_id, req.scene_id)

