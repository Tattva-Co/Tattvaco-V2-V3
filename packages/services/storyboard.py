"""Storyboard Intelligence service and run lifecycle.

Owns starting, executing, and deciding Storyboard Intelligence runs (Workflow G-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from langgraph.types import Command
from sqlalchemy.orm import Session

from packages.core.logging import get_logger
from packages.domain.enums import (
    STORYBOARD_INTELLIGENCE_GRAPH_ID,
    STORYBOARD_INTELLIGENCE_GRAPH_VERSION,
    ApprovalDecision,
    ApprovalStatus,
    AuditAction,
    WorkflowStatus,
)
from packages.domain.errors import InvalidStateError, NotFoundError
from packages.persistence.models import (
    ApprovalRequestModel,
    StoryboardPanelModel,
    WorkflowRunModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    OutboxRepository,
    ProjectRepository,
    StoryboardRepository,
    WorkflowRunRepository,
)
from packages.services.identity import ActorContext
from packages.services.script_review import record_decision
from packages.workflows.checkpointer import get_checkpointer
from packages.workflows.storyboard_intelligence.graph import build_storyboard_intelligence_graph

logger = get_logger("services.storyboard")


@dataclass
class StoryboardDecisionResult:
    approval_id: str
    decision: str
    run_status: str
    new_project_version: int


class StoryboardIntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.runs = WorkflowRunRepository(db)
        self.approvals = ApprovalRepository(db)
        self.audit = AuditRepository(db)

    def start(
        self,
        actor: ActorContext,
        project_id: str,
        brief: str | None = None,
        *,
        sync: bool = True,
    ) -> WorkflowRunModel:
        project = self.projects.get_scoped(project_id, actor.org_id)

        run = self.runs.add(
            WorkflowRunModel(
                graph_id=STORYBOARD_INTELLIGENCE_GRAPH_ID,
                graph_version=STORYBOARD_INTELLIGENCE_GRAPH_VERSION,
                project_id=project.id,
                organization_id=project.organization_id,
                actor_id=actor.user_id,
                expected_project_version=project.current_version,
                status=(WorkflowStatus.RUNNING if sync else WorkflowStatus.QUEUED).value,
                input_asset_ids=[],
                output_refs={"brief": brief},
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.WORKFLOW_STARTED,
            target_type="workflow_run",
            target_id=run.id,
            details={"graph_id": run.graph_id, "brief": brief, "mode": "sync" if sync else "queued"},
        )
        if not sync:
            OutboxRepository(self.db).enqueue(
                run.id, STORYBOARD_INTELLIGENCE_GRAPH_ID, {"workflow_run_id": run.id}
            )
        self.db.commit()

        if sync:
            self.execute(run.id)
        return self.runs.get(run.id)

    def execute(self, run_id: str) -> WorkflowRunModel:
        run = self.runs.get(run_id)
        if run is None:
            raise NotFoundError(f"Workflow run '{run_id}' not found.")
        run.status = WorkflowStatus.RUNNING.value
        self.db.commit()

        brief = (run.output_refs or {}).get("brief")
        initial_state = {
            "workflow_run_id": run.id,
            "project_id": run.project_id,
            "organization_id": run.organization_id,
            "actor_id": run.actor_id,
            "expected_project_version": run.expected_project_version,
            "brief": brief,
            "approval_status": "pending",
        }
        self._invoke(run.id, initial_state)
        self.db.expire_all()
        return self.runs.get(run.id)

    def decide(
        self,
        actor: ActorContext,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        notes: str | None = None,
        approved_panel_ids: Sequence[str] | None = None,
    ) -> StoryboardDecisionResult:
        approval: ApprovalRequestModel = self.approvals.get_scoped(
            approval_id, actor.org_id, for_update=True
        )
        if approval.status != ApprovalStatus.PENDING.value:
            raise InvalidStateError(f"Approval request already {approval.status}.")

        record_decision(approval, decision, actor.user_id, notes)
        self.audit.record(
            project_id=approval.project_id,
            organization_id=approval.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.APPROVAL_DECIDED,
            target_type="approval_request",
            target_id=approval.id,
            details={"decision": decision.value, "notes": notes},
        )
        self.db.commit()

        run_id = approval.workflow_run_id
        self._invoke(
            run_id,
            Command(
                resume={
                    "decision": decision.value,
                    "notes": notes,
                    "actor_id": actor.user_id,
                    "approved_panel_ids": approved_panel_ids,
                }
            ),
        )
        self.db.expire_all()
        run = self.runs.get(run_id)
        project = self.projects.get_scoped(run.project_id, actor.org_id)
        return StoryboardDecisionResult(
            approval_id=approval_id,
            decision=decision.value,
            run_status=run.status,
            new_project_version=project.current_version,
        )

    def _invoke(self, run_id: str, payload: dict | Command) -> None:
        graph = build_storyboard_intelligence_graph()
        try:
            with get_checkpointer() as checkpointer:
                app = graph.compile(checkpointer=checkpointer)
                app.invoke(payload, config={"configurable": {"thread_id": run_id}})
        except Exception as exc:
            logger.exception("Storyboard intelligence execution failed for run %s", run_id)
            self._mark_failed(run_id, str(exc))
            raise

        self._sync_run_status(run_id)

    def _sync_run_status(self, run_id: str) -> None:
        with get_checkpointer() as checkpointer:
            app = build_storyboard_intelligence_graph().compile(checkpointer=checkpointer)
            snapshot = app.get_state({"configurable": {"thread_id": run_id}})

        run = self.runs.get(run_id)
        if run is None:
            return

        approval = self.approvals.get_for_run(run_id)
        if snapshot.next:
            run.status = WorkflowStatus.AWAITING_APPROVAL.value
            if approval is not None:
                approval.status = ApprovalStatus.PENDING.value
        else:
            if approval is not None and approval.decision == ApprovalDecision.REJECTED.value:
                run.status = WorkflowStatus.REJECTED.value
            else:
                run.status = WorkflowStatus.COMPLETED.value
        self.db.commit()

    def _mark_failed(self, run_id: str, error_message: str) -> None:
        try:
            run = self.runs.get(run_id)
            if run is not None:
                run.status = WorkflowStatus.FAILED.value
                run.error_message = error_message
                self.db.commit()
        except Exception:
            logger.exception("Failed to mark run %s as failed", run_id)


class StoryboardService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.storyboard = StoryboardRepository(db)

    def list_panels(self, actor: ActorContext, project_id: str) -> list[StoryboardPanelModel]:
        self.projects.get_scoped(project_id, actor.org_id)
        return self.storyboard.list_panels_for_project(project_id)
