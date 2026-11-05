"""Human approval gate."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import ApprovalDecisionRequest, ApprovalDecisionResponse
from packages.domain.enums import (
    FILM_BIBLE_APPROVAL_SCOPE,
    HISTORICAL_RESEARCH_APPROVAL_SCOPE,
    SCRIPT_INTELLIGENCE_APPROVAL_SCOPE,
    STORYBOARD_INTELLIGENCE_APPROVAL_SCOPE,
)
from packages.domain.errors import ValidationFailure
from packages.persistence.repositories import ApprovalRepository
from packages.services.film_bible import FilmBibleSynthesisService
from packages.services.historical_research import HistoricalResearchService
from packages.services.identity import ActorContext
from packages.services.script_intelligence import ScriptIntelligenceService
from packages.services.storyboard import StoryboardIntelligenceService

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/{approval_id}/decide", response_model=ApprovalDecisionResponse)
def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    approval = ApprovalRepository(db).get_scoped(approval_id, actor.org_id)
    if approval.scope == HISTORICAL_RESEARCH_APPROVAL_SCOPE:
        result = HistoricalResearchService(db).decide(
            actor,
            approval_id,
            req.decision,
            notes=req.notes,
            approved_claim_ids=req.approved_claim_ids,
            approved_question_ids=req.approved_question_ids,
        )
    elif approval.scope == STORYBOARD_INTELLIGENCE_APPROVAL_SCOPE:
        result = StoryboardIntelligenceService(db).decide(
            actor,
            approval_id,
            req.decision,
            notes=req.notes,
            approved_panel_ids=req.approved_panel_ids,
        )
    elif approval.scope == FILM_BIBLE_APPROVAL_SCOPE:
        result = FilmBibleSynthesisService(db).decide(
            actor,
            approval_id,
            req.decision,
            notes=req.notes,
            approved_rule_ids=req.approved_rule_ids,
        )
    elif approval.scope == SCRIPT_INTELLIGENCE_APPROVAL_SCOPE:
        result = ScriptIntelligenceService(db).decide(
            actor,
            approval_id,
            req.decision,
            notes=req.notes,
            approved_scene_ids=req.approved_scene_ids,
            approved_entity_ids=req.approved_entity_ids,
        )
    else:
        # SEC-08 (docs/audit/08): an unrecognised scope must not be silently routed to
        # whichever service happens to be the fallback branch.
        raise ValidationFailure(f"Unknown approval scope: {approval.scope!r}")
    return ApprovalDecisionResponse(
        approval_id=result.approval_id,
        decision=result.decision,
        run_status=result.run_status,
        new_project_version=result.new_project_version,
    )
