"""Location/environment profile versioning, the legacy location link, and scene-level
environment states (D5, S-ENV-01)."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    EnvironmentStateCreateRequest,
    EnvironmentStateResponse,
    LocationAdoptResponse,
    LocationDecisionRequest,
    LocationDetailResponse,
    LocationVersionProposeRequest,
    LocationVersionProposeResponse,
    LocationVersionResponse,
)
from packages.services.identity import ActorContext
from packages.services.locations import LocationService

router = APIRouter(prefix="/projects/{project_id}/locations", tags=["locations"])


@router.get("/{location_id}", response_model=LocationDetailResponse)
def get_location_detail(project_id: str, location_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    location, current = LocationService(db).get_detail(actor, project_id, location_id)
    return LocationDetailResponse(
        id=location.id,
        canonical_name=location.canonical_name,
        aliases=location.aliases,
        current_version=LocationVersionResponse.model_validate(current) if current else None,
    )


@router.get("/{location_id}/versions", response_model=List[LocationVersionResponse])
def list_location_versions(project_id: str, location_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return LocationService(db).list_versions(actor, project_id, location_id)


@router.post(
    "/{location_id}/versions", response_model=LocationVersionProposeResponse, status_code=status.HTTP_201_CREATED
)
def propose_location_version(
    project_id: str,
    location_id: str,
    req: LocationVersionProposeRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    version, approval = LocationService(db).propose_version(actor, project_id, location_id, profile_patch=req.profile_patch)
    return LocationVersionProposeResponse(
        version=LocationVersionResponse.model_validate(version), approval_request_id=approval.id
    )


@router.post("/{location_id}/versions/{version_id}/decide", response_model=LocationVersionResponse)
def decide_location_version(
    project_id: str,
    location_id: str,
    version_id: str,
    req: LocationDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return LocationService(db).decide_version(actor, project_id, version_id, req.decision, req.notes)


@router.post("/{location_id}/adopt", response_model=LocationAdoptResponse)
def adopt_location(project_id: str, location_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    matched = LocationService(db).adopt_legacy_location(actor, project_id, location_id)
    return LocationAdoptResponse(matched_scene_ids=matched)


# -- Environment states (TFD-ENV-002) ------------------------------------------------

environment_states_router = APIRouter(prefix="/projects/{project_id}/environment-states", tags=["locations"])


@environment_states_router.get("", response_model=EnvironmentStateResponse | None)
def get_effective_environment_state(
    project_id: str, scene_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return LocationService(db).get_effective_environment_state(actor, project_id, scene_id)


@environment_states_router.post("", response_model=EnvironmentStateResponse, status_code=status.HTTP_201_CREATED)
def create_environment_state(
    project_id: str, req: EnvironmentStateCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return LocationService(db).create_environment_state(
        actor, project_id, req.scene_id, changes=req.changes, location_id=req.location_id
    )
