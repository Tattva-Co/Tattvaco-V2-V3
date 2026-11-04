"""Historical Research endpoints (questions, sources, claims, conflicts)."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    ResearchClaimResponse,
    ResearchConflictResponse,
    ResearchQuestionCreateRequest,
    ResearchQuestionResponse,
    ResearchSourceCreateRequest,
    ResearchSourceResponse,
)
from packages.services.identity import ActorContext
from packages.services.research import ResearchService

router = APIRouter(prefix="/projects/{project_id}/research", tags=["research"])


@router.get("/questions", response_model=List[ResearchQuestionResponse])
def list_questions(
    project_id: str,
    status: str | None = None,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ResearchService(db).list_questions(actor, project_id, status=status)


@router.post("/questions", response_model=ResearchQuestionResponse)
def create_question(
    project_id: str,
    req: ResearchQuestionCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ResearchService(db).create_question(
        actor, project_id, text=req.text, category=req.category
    )


@router.get("/sources", response_model=List[ResearchSourceResponse])
def list_sources(
    project_id: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ResearchService(db).list_sources(actor, project_id)


@router.post("/sources", response_model=ResearchSourceResponse)
def create_source(
    project_id: str,
    req: ResearchSourceCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ResearchService(db).create_source(
        actor,
        project_id,
        title=req.title,
        tier=req.tier,
        author=req.author,
        publication_year=req.publication_year,
        locator=req.locator,
        url=req.url,
        asset_id=req.asset_id,
        reliability_notes=req.reliability_notes,
    )


@router.get("/claims", response_model=List[ResearchClaimResponse])
def list_claims(
    project_id: str,
    claim_class: str | None = None,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ResearchService(db).list_claims(actor, project_id, claim_class=claim_class)


@router.get("/conflicts", response_model=List[ResearchConflictResponse])
def list_conflicts(
    project_id: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ResearchService(db).list_conflicts(actor, project_id)

