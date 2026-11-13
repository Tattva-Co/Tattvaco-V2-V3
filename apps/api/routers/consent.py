"""Performer registry, consent and the voice-profile consent gate (D4, S-DH-01).

Performer and consent creation return 403 ``policy_pending`` while DEC-007/DEC-012
remain open (AT-CNS-002.2) -- see ``packages.core.config.Settings.consent_policy_approved``.
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    ConsentCheckResponse,
    ConsentCreateRequest,
    ConsentCreateResponse,
    ConsentDecisionRequest,
    ConsentResponse,
    ConsentRevokeRequest,
    PerformerCreateRequest,
    PerformerResponse,
    VoiceProfileCreateRequest,
    VoiceProfileResponse,
)
from packages.persistence.repositories import (
    PerformerConsentRepository,
    PerformerRepository,
    ProjectRepository,
)
from packages.services.authz import AuthzService
from packages.services.consent import ConsentService, PerformerService, VoiceProfileService
from packages.services.identity import ActorContext

router = APIRouter(tags=["consent"])


@router.get("/projects/{project_id}/performers", response_model=List[PerformerResponse])
def list_performers(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return PerformerService(db).list_performers(actor, project_id)


@router.post("/projects/{project_id}/performers", response_model=PerformerResponse, status_code=status.HTTP_201_CREATED)
def create_performer(
    project_id: str, req: PerformerCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return PerformerService(db).create_performer(actor, project_id, req.display_name, req.notes)


@router.get("/projects/{project_id}/performers/{performer_id}/consents", response_model=List[ConsentResponse])
def list_consents(
    project_id: str, performer_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    project = ProjectRepository(db).get_scoped(project_id, actor.org_id)
    performer = PerformerRepository(db).get_scoped(performer_id, project.organization_id)
    return PerformerConsentRepository(db).list_for_performer(performer.id)


@router.post(
    "/projects/{project_id}/performers/{performer_id}/consents",
    response_model=ConsentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_consent(
    project_id: str,
    performer_id: str,
    req: ConsentCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    consent, approval = ConsentService(db).create_consent(
        actor,
        project_id,
        performer_id,
        req.purpose,
        project_scope=req.project_scope,
        valid_from=req.valid_from,
        valid_until=req.valid_until,
        document_asset_id=req.document_asset_id,
        template_version=req.template_version,
    )
    return ConsentCreateResponse(consent=ConsentResponse.model_validate(consent), approval_request_id=approval.id)


@router.post("/projects/{project_id}/consents/{consent_id}/decide", response_model=ConsentResponse)
def decide_consent(
    project_id: str,
    consent_id: str,
    req: ConsentDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ConsentService(db).decide_consent(actor, project_id, consent_id, req.decision, req.notes)


@router.post("/projects/{project_id}/consents/revoke", response_model=ConsentResponse)
def revoke_consent(
    project_id: str, req: ConsentRevokeRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ConsentService(db).revoke(actor, project_id, req.performer_id, req.purpose, req.reason)


@router.get("/projects/{project_id}/consent-checks", response_model=ConsentCheckResponse)
def check_consent(
    project_id: str,
    performer_id: str,
    purpose: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    project = ProjectRepository(db).get_scoped(project_id, actor.org_id)
    AuthzService(db).require(actor, "project.read", project)
    evaluation = ConsentService(db).evaluate(performer_id, purpose, project_id)
    return ConsentCheckResponse(allowed=evaluation.allowed, reason=evaluation.reason)


# -- Voice profiles (TFD-CNS-005) --------------------------------------------------


@router.get("/projects/{project_id}/voice-profiles", response_model=List[VoiceProfileResponse])
def list_voice_profiles(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return VoiceProfileService(db).list_voice_profiles(actor, project_id)


@router.post("/projects/{project_id}/voice-profiles", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
def create_voice_profile(
    project_id: str, req: VoiceProfileCreateRequest, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return VoiceProfileService(db).create_voice_profile(
        actor, project_id, kind=req.kind, character_id=req.character_id, performer_id=req.performer_id
    )
