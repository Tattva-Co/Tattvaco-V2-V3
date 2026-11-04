"""Workflow run endpoints (Script Intelligence G-01)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    HistoricalResearchTriggerRequest,
    StoryboardTriggerRequest,
    WorkflowRunResponse,
    WorkflowTriggerRequest,
    WorkflowTriggerResponse,
)
from packages.persistence.repositories import ApprovalRepository, WorkflowRunRepository
from packages.services.historical_research import HistoricalResearchService
from packages.services.identity import ActorContext
from packages.services.script_intelligence import ScriptIntelligenceService
from packages.services.storyboard import StoryboardIntelligenceService

router = APIRouter(tags=["workflows"])


@router.post(
    "/projects/{project_id}/workflows/script-intelligence",
    response_model=WorkflowTriggerResponse,
)
def trigger_script_intelligence(
    project_id: str,
    req: WorkflowTriggerRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    run = ScriptIntelligenceService(db).start(
        actor, project_id, req.script_asset_id, sync=req.sync_execution
    )
    approval = ApprovalRepository(db).get_pending_for_run(run.id)
    return WorkflowTriggerResponse(
        workflow_run_id=run.id,
        status=run.status,
        approval_request_id=approval.id if approval else None,
        candidate_summary=approval.candidate_summary if approval else {},
    )


@router.post(
    "/projects/{project_id}/workflows/historical-research",
    response_model=WorkflowTriggerResponse,
)
def trigger_historical_research(
    project_id: str,
    req: HistoricalResearchTriggerRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    run = HistoricalResearchService(db).start(
        actor, project_id, req.topic, seed_text=req.seed_text, sync=req.sync_execution
    )
    approval = ApprovalRepository(db).get_pending_for_run(run.id)
    return WorkflowTriggerResponse(
        workflow_run_id=run.id,
        status=run.status,
        approval_request_id=approval.id if approval else None,
        candidate_summary=approval.candidate_summary if approval else {},
    )


@router.post(
    "/projects/{project_id}/workflows/storyboard-intelligence",
    response_model=WorkflowTriggerResponse,
)
def trigger_storyboard_intelligence(
    project_id: str,
    req: StoryboardTriggerRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    run = StoryboardIntelligenceService(db).start(
        actor, project_id, brief=req.brief, sync=req.sync_execution
    )
    approval = ApprovalRepository(db).get_pending_for_run(run.id)
    return WorkflowTriggerResponse(
        workflow_run_id=run.id,
        status=run.status,
        approval_request_id=approval.id if approval else None,
        candidate_summary=approval.candidate_summary if approval else {},
    )


@router.get("/workflow-runs/{run_id}", response_model=WorkflowRunResponse)
def get_workflow_run(run_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return WorkflowRunRepository(db).get_scoped(run_id, actor.org_id)
