"""Cinematography Bible (camera/lens/lighting libraries, versioned bible) and AI shot
recommendations with override (D6, S-CIN-01)."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    CameraProfileCreateRequest,
    CameraProfileResponse,
    CinematographyDecisionRequest,
    CinematographyOverrideRequest,
    CinematographyRecommendationRequest,
    CinematographyRecommendationResponse,
    CinematographyVersionProposeRequest,
    CinematographyVersionProposeResponse,
    CinematographyVersionResponse,
    LensProfileCreateRequest,
    LensProfileResponse,
    LightingProfileCreateRequest,
    LightingProfileResponse,
)
from packages.services.cinematography import CinematographyService
from packages.services.identity import ActorContext

router = APIRouter(prefix="/projects/{project_id}/cinematography", tags=["cinematography"])


@router.get("/camera-profiles", response_model=List[CameraProfileResponse])
def list_camera_profiles(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CinematographyService(db).list_camera_profiles(actor, project_id)


@router.post("/camera-profiles", response_model=CameraProfileResponse, status_code=status.HTTP_201_CREATED)
def create_camera_profile(
    project_id: str, req: CameraProfileCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return CinematographyService(db).create_camera_profile(actor, project_id, name=req.name, spec_kind=req.spec_kind, specs=req.specs)


@router.get("/lens-profiles", response_model=List[LensProfileResponse])
def list_lens_profiles(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CinematographyService(db).list_lens_profiles(actor, project_id)


@router.post("/lens-profiles", response_model=LensProfileResponse, status_code=status.HTTP_201_CREATED)
def create_lens_profile(
    project_id: str, req: LensProfileCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return CinematographyService(db).create_lens_profile(actor, project_id, name=req.name, specs=req.specs)


@router.get("/lighting-profiles", response_model=List[LightingProfileResponse])
def list_lighting_profiles(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CinematographyService(db).list_lighting_profiles(actor, project_id)


@router.post("/lighting-profiles", response_model=LightingProfileResponse, status_code=status.HTTP_201_CREATED)
def create_lighting_profile(
    project_id: str, req: LightingProfileCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return CinematographyService(db).create_lighting_profile(actor, project_id, name=req.name, specs=req.specs)


@router.get("/profile", response_model=CinematographyVersionResponse | None)
def get_current_bible(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CinematographyService(db).get_current_bible(actor, project_id)


@router.get("/profile/versions", response_model=List[CinematographyVersionResponse])
def list_bible_versions(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CinematographyService(db).list_versions(actor, project_id)


@router.post("/profile/versions", response_model=CinematographyVersionProposeResponse, status_code=status.HTTP_201_CREATED)
def propose_bible_version(
    project_id: str,
    req: CinematographyVersionProposeRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    version, approval = CinematographyService(db).propose_bible_version(
        actor,
        project_id,
        camera_profile_ids=req.camera_profile_ids,
        lens_profile_ids=req.lens_profile_ids,
        lighting_profile_ids=req.lighting_profile_ids,
        composition_rules=req.composition_rules,
        virtual_camera_profile=req.virtual_camera_profile,
        visual_language=req.visual_language,
    )
    return CinematographyVersionProposeResponse(
        version=CinematographyVersionResponse.model_validate(version), approval_request_id=approval.id
    )


@router.post("/profile/versions/{version_id}/decide", response_model=CinematographyVersionResponse)
def decide_bible_version(
    project_id: str,
    version_id: str,
    req: CinematographyDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return CinematographyService(db).decide_version(actor, project_id, version_id, req.decision, req.notes)


@router.get("/recommendations", response_model=List[CinematographyRecommendationResponse])
def list_recommendations(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return CinematographyService(db).list_recommendations(actor, project_id)


@router.post("/recommendations", response_model=CinematographyRecommendationResponse, status_code=status.HTTP_201_CREATED)
def request_recommendation(
    project_id: str, req: CinematographyRecommendationRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return CinematographyService(db).request_recommendation(actor, project_id, req.intent)


@router.post("/recommendations/{recommendation_id}/override", response_model=CinematographyRecommendationResponse)
def override_recommendation(
    project_id: str,
    recommendation_id: str,
    req: CinematographyOverrideRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return CinematographyService(db).override_recommendation(
        actor, project_id, recommendation_id, field_name=req.field_name, value=req.value
    )
