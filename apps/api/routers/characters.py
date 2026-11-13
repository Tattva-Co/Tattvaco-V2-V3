"""Character identity, physical profile versioning, facial references, character
states and body measurements (D4, S-CHR-01, S-PHY-01)."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    CharacterDecisionRequest,
    CharacterDetailResponse,
    CharacterFacialReferenceCreateRequest,
    CharacterFacialReferenceResponse,
    CharacterStateCreateRequest,
    CharacterStateResponse,
    CharacterVersionProposeRequest,
    CharacterVersionProposeResponse,
    CharacterVersionResponse,
    MeasurementCorrectRequest,
    MeasurementCreateRequest,
    MeasurementResponse,
)
from packages.services.characters import CharacterService
from packages.services.identity import ActorContext
from packages.services.measurements import MeasurementService

router = APIRouter(prefix="/projects/{project_id}/characters", tags=["characters"])


@router.get("/{character_id}", response_model=CharacterDetailResponse)
def get_character_detail(project_id: str, character_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    character, current = CharacterService(db).get_detail(actor, project_id, character_id)
    return CharacterDetailResponse(
        id=character.id,
        canonical_name=character.canonical_name,
        aliases=character.aliases,
        performer_id=character.performer_id,
        current_version=CharacterVersionResponse.model_validate(current) if current else None,
    )


@router.get("/{character_id}/versions", response_model=List[CharacterVersionResponse])
def list_character_versions(project_id: str, character_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CharacterService(db).list_versions(actor, project_id, character_id)


@router.post(
    "/{character_id}/versions", response_model=CharacterVersionProposeResponse, status_code=status.HTTP_201_CREATED
)
def propose_character_version(
    project_id: str,
    character_id: str,
    req: CharacterVersionProposeRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    version, approval = CharacterService(db).propose_version(
        actor, project_id, character_id, identity_patch=req.identity_patch, physical_patch=req.physical_patch
    )
    return CharacterVersionProposeResponse(
        version=CharacterVersionResponse.model_validate(version), approval_request_id=approval.id
    )


@router.post("/{character_id}/versions/{version_id}/decide", response_model=CharacterVersionResponse)
def decide_character_version(
    project_id: str,
    character_id: str,
    version_id: str,
    req: CharacterDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return CharacterService(db).decide_version(actor, project_id, version_id, req.decision, req.notes)


@router.get("/{character_id}/facial-references", response_model=List[CharacterFacialReferenceResponse])
def list_facial_references(project_id: str, character_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CharacterService(db).list_facial_references(actor, project_id, character_id)


@router.post(
    "/{character_id}/facial-references",
    response_model=CharacterFacialReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_facial_reference(
    project_id: str,
    character_id: str,
    req: CharacterFacialReferenceCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return CharacterService(db).add_facial_reference(
        actor, project_id, character_id, asset_id=req.asset_id, role=req.role, facial_identity_version=req.facial_identity_version
    )


@router.get("/{character_id}/states", response_model=List[CharacterStateResponse])
def list_character_states(project_id: str, character_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CharacterService(db).list_states(actor, project_id, character_id)


@router.post("/{character_id}/states", response_model=CharacterStateResponse, status_code=status.HTTP_201_CREATED)
def create_character_state(
    project_id: str,
    character_id: str,
    req: CharacterStateCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return CharacterService(db).create_state(
        actor,
        project_id,
        character_id,
        state_label=req.state_label,
        applies_from_scene_id=req.applies_from_scene_id,
        applies_until_scene_id=req.applies_until_scene_id,
        deltas=req.deltas,
        evidence_refs=req.evidence_refs,
    )


@router.get("/{character_id}/effective-state", response_model=CharacterStateResponse | None)
def get_effective_state(
    project_id: str,
    character_id: str,
    scene_number: int,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return CharacterService(db).effective_state(actor, project_id, character_id, scene_number)


# -- Body measurements (TFD-PHY-001/002/003/004/006) -------------------------------

measurements_router = APIRouter(prefix="/projects/{project_id}/measurements", tags=["measurements"])


@measurements_router.get("", response_model=List[MeasurementResponse])
def get_measurement_history(
    project_id: str,
    subject_type: str,
    subject_id: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return MeasurementService(db).history(actor, project_id, subject_type, subject_id)


@measurements_router.post("", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def save_measurement(
    project_id: str,
    req: MeasurementCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return MeasurementService(db).save_measurement(
        actor,
        project_id,
        subject_type=req.subject_type,
        subject_id=req.subject_id,
        measurement_key=req.measurement_key,
        value=req.value,
        unit=req.unit,
        capture_method=req.capture_method,
        confidence=req.confidence,
        source_asset_id=req.source_asset_id,
        capture_device_or_tool=req.capture_device_or_tool,
        notes=req.notes,
    )


@measurements_router.post("/{measurement_id}/correct", response_model=MeasurementResponse)
def correct_measurement(
    project_id: str,
    measurement_id: str,
    req: MeasurementCorrectRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return MeasurementService(db).correct_measurement(
        actor, project_id, measurement_id, value=req.value, unit=req.unit, notes=req.notes
    )


@measurements_router.post("/{measurement_id}/verify", response_model=MeasurementResponse)
def verify_measurement(
    project_id: str, measurement_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return MeasurementService(db).verify_measurement(actor, project_id, measurement_id)
