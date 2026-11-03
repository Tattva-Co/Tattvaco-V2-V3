"""Human approval gate."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import ApprovalDecisionRequest, ApprovalDecisionResponse
from packages.services.identity import ActorContext
from packages.services.script_intelligence import ScriptIntelligenceService

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/{approval_id}/decide", response_model=ApprovalDecisionResponse)
def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    result = ScriptIntelligenceService(db).decide(
        actor,
        approval_id,
        req.decision,
        notes=req.notes,
        approved_scene_ids=req.approved_scene_ids,
        approved_entity_ids=req.approved_entity_ids,
    )
    return ApprovalDecisionResponse(
        approval_id=result.approval_id,
        decision=result.decision,
        run_status=result.run_status,
        new_project_version=result.new_project_version,
    )
