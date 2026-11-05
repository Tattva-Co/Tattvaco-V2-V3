"""Film Bible endpoints (canonical visual-world rules)."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import FilmBibleRuleCreateRequest, FilmBibleRuleResponse
from packages.services.film_bible import FilmBibleService
from packages.services.identity import ActorContext

router = APIRouter(prefix="/projects/{project_id}/film-bible", tags=["film-bible"])


@router.get("/rules", response_model=List[FilmBibleRuleResponse])
def list_rules(
    project_id: str,
    category: str | None = None,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return FilmBibleService(db).list_rules(actor, project_id, category=category)


@router.post("/rules", response_model=FilmBibleRuleResponse)
def create_rule(
    project_id: str,
    req: FilmBibleRuleCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return FilmBibleService(db).create_rule(
        actor,
        project_id,
        category=req.category,
        title=req.title,
        rule_text=req.rule_text,
        negative_prompt_guidance=req.negative_prompt_guidance,
        strictness=req.strictness,
        historical_claim_id=req.historical_claim_id,
        rationale=req.rationale,
    )

