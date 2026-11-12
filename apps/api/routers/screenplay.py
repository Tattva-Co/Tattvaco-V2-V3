"""Screenplay governance (D2): import, revisions, suggestions, lock/approval, impact
analysis."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    ImpactAnalysisResponse,
    ImpactPreviewResponse,
    ScreenplayDecisionRequest,
    ScreenplayDecisionResponse,
    ScreenplayDiffResponse,
    ScreenplaySubmitRequest,
    ScreenplaySuggestionDecisionRequest,
    ScreenplaySuggestionGenerateRequest,
    ScreenplaySuggestionResponse,
    ScreenplayVersionImportRequest,
    ScreenplayVersionResponse,
    ScreenplayVersionUpdateRequest,
)
from packages.services.identity import ActorContext
from packages.services.screenplay import ScreenplayGovernanceService

router = APIRouter(prefix="/projects/{project_id}", tags=["screenplay"])


@router.post("/screenplay-versions", response_model=ScreenplayVersionResponse, status_code=201)
def import_screenplay_version(
    project_id: str,
    req: ScreenplayVersionImportRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ScreenplayGovernanceService(db).import_version(
        actor, project_id, req.source_asset_id, episode_id=req.episode_id
    )


@router.get("/screenplay-versions", response_model=List[ScreenplayVersionResponse])
def list_screenplay_versions(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ScreenplayGovernanceService(db).list_versions(actor, project_id)


@router.get("/screenplay-versions/{version_id}", response_model=ScreenplayVersionResponse)
def get_screenplay_version(
    project_id: str, version_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ScreenplayGovernanceService(db).get_version(actor, project_id, version_id)


@router.patch("/screenplay-versions/{version_id}", response_model=ScreenplayVersionResponse)
def update_screenplay_version(
    project_id: str,
    version_id: str,
    req: ScreenplayVersionUpdateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ScreenplayGovernanceService(db).update_content(actor, project_id, version_id, req.content_text)


@router.get("/screenplay-versions/{version_id}/diff", response_model=ScreenplayDiffResponse)
def diff_screenplay_version(
    project_id: str,
    version_id: str,
    against: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ScreenplayGovernanceService(db).diff(actor, project_id, version_id, against)


@router.post("/screenplay-versions/{version_id}/revise", response_model=ScreenplayVersionResponse, status_code=201)
def create_screenplay_revision(
    project_id: str, version_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ScreenplayGovernanceService(db).create_revision(actor, project_id, version_id)


@router.post("/screenplay-versions/{version_id}/submit", response_model=ScreenplayVersionResponse)
def submit_screenplay_revision(
    project_id: str,
    version_id: str,
    req: ScreenplaySubmitRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ScreenplayGovernanceService(db).submit_for_review(actor, project_id, version_id, req.justification)


@router.post("/screenplay-versions/{version_id}/decide", response_model=ScreenplayDecisionResponse)
def decide_screenplay_revision(
    project_id: str,
    version_id: str,
    req: ScreenplayDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    result = ScreenplayGovernanceService(db).decide_revision(actor, project_id, version_id, req.decision, req.notes)
    return ScreenplayDecisionResponse(
        approval_id=result.approval_id,
        decision=result.decision,
        version_status=result.version_status,
        is_canonical=result.is_canonical,
    )


@router.post("/screenplay-versions/{version_id}/confirm-legacy-lock", response_model=ScreenplayVersionResponse)
def confirm_legacy_lock(
    project_id: str, version_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ScreenplayGovernanceService(db).confirm_legacy_lock(actor, project_id, version_id)


@router.get("/screenplay-versions/{version_id}/impact-preview", response_model=ImpactPreviewResponse)
def preview_impact(
    project_id: str, version_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ScreenplayGovernanceService(db).preview_impact(actor, project_id, version_id)


@router.post(
    "/screenplay-versions/{version_id}/suggestions/generate",
    response_model=List[ScreenplaySuggestionResponse],
    status_code=201,
)
def generate_suggestions(
    project_id: str,
    version_id: str,
    req: ScreenplaySuggestionGenerateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ScreenplayGovernanceService(db).generate_suggestions(actor, project_id, version_id, req.scope_notes)


@router.get("/screenplay-versions/{version_id}/suggestions", response_model=List[ScreenplaySuggestionResponse])
def list_suggestions(
    project_id: str, version_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ScreenplayGovernanceService(db).list_suggestions(actor, project_id, version_id)


@router.post("/screenplay-suggestions/{suggestion_id}/decide", response_model=ScreenplaySuggestionResponse)
def decide_suggestion(
    project_id: str,
    suggestion_id: str,
    req: ScreenplaySuggestionDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ScreenplayGovernanceService(db).decide_suggestion(
        actor, project_id, suggestion_id, req.disposition, req.notes
    )


@router.get("/impact-analyses", response_model=List[ImpactAnalysisResponse])
def list_impact_analyses(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ScreenplayGovernanceService(db).list_impact_analyses(actor, project_id)
