"""Props and weapons register, and per-scene prop holder tracking (D5, S-CST-02)."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import PropCreateRequest, PropResponse, PropStateCreateRequest, PropStateResponse
from packages.services.identity import ActorContext
from packages.services.props import PropService

router = APIRouter(prefix="/projects/{project_id}/props", tags=["props"])


@router.get("", response_model=List[PropResponse])
def list_props(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return PropService(db).list_props(actor, project_id)


@router.post("", response_model=PropResponse, status_code=status.HTTP_201_CREATED)
def create_prop(project_id: str, req: PropCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return PropService(db).create_prop(
        actor,
        project_id,
        name=req.name,
        kind=req.kind,
        prop_type=req.type,
        design=req.design,
        material=req.material,
        scale=req.scale,
        owner_character_id=req.owner_character_id,
    )


@router.get("/{prop_id}/states", response_model=List[PropStateResponse])
def list_prop_states(project_id: str, prop_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return PropService(db).list_states(actor, project_id, prop_id)


@router.post("/{prop_id}/states", response_model=PropStateResponse, status_code=status.HTTP_201_CREATED)
def create_prop_state(
    project_id: str, prop_id: str, req: PropStateCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return PropService(db).create_state(
        actor, project_id, prop_id, scene_id=req.scene_id, holder_character_id=req.holder_character_id, notes=req.notes
    )
