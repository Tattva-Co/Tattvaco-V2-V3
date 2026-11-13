"""Costume Bible, costume states, costume assignment and continuity findings (D5,
S-CST-01)."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    ContinuityFindingResponse,
    CostumeAssignmentCreateRequest,
    CostumeAssignmentResponse,
    CostumeCreateRequest,
    CostumeDecisionRequest,
    CostumeDetailResponse,
    CostumeResponse,
    CostumeStateCreateRequest,
    CostumeStateResponse,
    CostumeVersionProposeRequest,
    CostumeVersionProposeResponse,
    CostumeVersionResponse,
)
from packages.services.costumes import CostumeService
from packages.services.identity import ActorContext

router = APIRouter(prefix="/projects/{project_id}/costumes", tags=["costumes"])


@router.get("", response_model=List[CostumeResponse])
def list_costumes(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CostumeService(db).list_costumes(actor, project_id)


@router.post("", response_model=CostumeResponse, status_code=status.HTTP_201_CREATED)
def create_costume(project_id: str, req: CostumeCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CostumeService(db).create_costume(actor, project_id, name=req.name, character_id=req.character_id)


@router.get("/{costume_id}", response_model=CostumeDetailResponse)
def get_costume_detail(project_id: str, costume_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    costume, current = CostumeService(db).get_detail(actor, project_id, costume_id)
    return CostumeDetailResponse(
        id=costume.id,
        name=costume.name,
        character_id=costume.character_id,
        current_version=CostumeVersionResponse.model_validate(current) if current else None,
    )


@router.get("/{costume_id}/versions", response_model=List[CostumeVersionResponse])
def list_costume_versions(project_id: str, costume_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CostumeService(db).list_versions(actor, project_id, costume_id)


@router.post(
    "/{costume_id}/versions", response_model=CostumeVersionProposeResponse, status_code=status.HTTP_201_CREATED
)
def propose_costume_version(
    project_id: str,
    costume_id: str,
    req: CostumeVersionProposeRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    version, approval = CostumeService(db).propose_version(
        actor, project_id, costume_id, profile_patch=req.profile_patch, claim_links=req.claim_links
    )
    return CostumeVersionProposeResponse(
        version=CostumeVersionResponse.model_validate(version), approval_request_id=approval.id
    )


@router.post("/{costume_id}/versions/{version_id}/decide", response_model=CostumeVersionResponse)
def decide_costume_version(
    project_id: str,
    costume_id: str,
    version_id: str,
    req: CostumeDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return CostumeService(db).decide_version(actor, project_id, version_id, req.decision, req.notes)


@router.get("/{costume_id}/states", response_model=List[CostumeStateResponse])
def list_costume_states(project_id: str, costume_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CostumeService(db).list_states(actor, project_id, costume_id)


@router.post("/{costume_id}/states", response_model=CostumeStateResponse, status_code=status.HTTP_201_CREATED)
def create_costume_state(
    project_id: str,
    costume_id: str,
    req: CostumeStateCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return CostumeService(db).create_state(actor, project_id, costume_id, state_label=req.state_label, deltas=req.deltas)


# -- Costume assignment + continuity findings (TFD-CST-003) -------------------------

assignments_router = APIRouter(prefix="/projects/{project_id}/costume-assignments", tags=["costumes"])


@assignments_router.post("", response_model=CostumeAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_costume_assignment(
    project_id: str, req: CostumeAssignmentCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return CostumeService(db).assign(
        actor,
        project_id,
        character_id=req.character_id,
        scene_id=req.scene_id,
        costume_id=req.costume_id,
        costume_state_id=req.costume_state_id,
    )


continuity_findings_router = APIRouter(prefix="/projects/{project_id}/continuity-findings", tags=["costumes"])


@continuity_findings_router.get("", response_model=List[ContinuityFindingResponse])
def list_continuity_findings(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CostumeService(db).list_continuity_findings(actor, project_id)
