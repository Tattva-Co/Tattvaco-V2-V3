"""Script Intelligence run lifecycle: start, execute (API or worker), and decide.

Used by the API (synchronous development path), the worker (durable outbox path) and,
in future, any other entry point. Owns run status transitions and the rule that a human
decision is persisted *before* the graph is resumed (ADR-001 invariant 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from langgraph.types import Command
from sqlalchemy.orm import Session

from packages.core.logging import get_logger
from packages.domain.enums import (
    SCRIPT_INTELLIGENCE_GRAPH_ID,
    SCRIPT_INTELLIGENCE_GRAPH_VERSION,
    ApprovalDecision,
    ApprovalStatus,
    AuditAction,
    WorkflowStatus,
)
from packages.domain.errors import InvalidStateError, NotFoundError
from packages.persistence.models import ApprovalRequestModel, WorkflowRunModel
from packages.persistence.repositories import (
    ApprovalRepository,
    AssetRepository,
    AuditRepository,
    OutboxRepository,
    ProjectRepository,
    WorkflowRunRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext
from packages.services.script_review import record_decision
from packages.workflows.checkpointer import get_checkpointer
from packages.workflows.script_intelligence.graph import build_script_intelligence_graph

logger = get_logger("services.script_intelligence")


@dataclass
class DecisionResult:
    approval_id: str
    decision: str
    run_status: str
    new_project_version: int


class ScriptIntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.runs = WorkflowRunRepository(db)
        self.approvals = ApprovalRepository(db)
        self.audit = AuditRepository(db)
        self.authz = AuthzService(db)

    # -- start ---------------------------------------------------------------

    def start(
        self,
        actor: ActorContext,
        project_id: str,
        script_asset_id: str,
        *,
        sync: bool,
    ) -> WorkflowRunModel:
        """Create a run. Executes inline when ``sync``; otherwise queues it for the worker."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "workflow.run", project)
        asset = AssetRepository(self.db).get_for_project(script_asset_id, project.id)

        run = self.runs.add(
            WorkflowRunModel(
                graph_id=SCRIPT_INTELLIGENCE_GRAPH_ID,
                graph_version=SCRIPT_INTELLIGENCE_GRAPH_VERSION,
                project_id=project.id,
                organization_id=project.organization_id,
                actor_id=actor.user_id,
                expected_project_version=project.current_version,
                status=(WorkflowStatus.RUNNING if sync else WorkflowStatus.QUEUED).value,
                input_asset_ids=[asset.id],
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.WORKFLOW_STARTED,
            target_type="workflow_run",
            target_id=run.id,
            details={"graph_id": run.graph_id, "script_asset_id": asset.id, "mode": "sync" if sync else "queued"},
        )
        if not sync:
            OutboxRepository(self.db).enqueue(
                run.id, SCRIPT_INTELLIGENCE_GRAPH_ID, {"workflow_run_id": run.id}
            )
        self.db.commit()

        if sync:
            self.execute(run.id)
        return self.runs.get(run.id)

    # -- execute -------------------------------------------------------------

    def execute(self, run_id: str) -> WorkflowRunModel:
        """Run the graph from the start until the human approval interrupt."""
        run = self.runs.get(run_id)
        if run is None:
            raise NotFoundError(f"Workflow run '{run_id}' not found.")
        run.status = WorkflowStatus.RUNNING.value
        self.db.commit()

        initial_state = {
            "workflow_run_id": run.id,
            "project_id": run.project_id,
            "organization_id": run.organization_id,
            "actor_id": run.actor_id,
            "expected_project_version": run.expected_project_version,
            "script_asset_id": run.input_asset_ids[0],
            "approval_status": "pending",
        }
        self._invoke(run.id, initial_state)
        self.db.expire_all()
        return self.runs.get(run.id)

    # -- decide --------------------------------------------------------------

    def decide(
        self,
        actor: ActorContext,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        notes: str | None = None,
        approved_scene_ids: Sequence[str] | None = None,
        approved_entity_ids: Sequence[str] | None = None,
    ) -> DecisionResult:
        approval: ApprovalRequestModel = self.approvals.get_scoped(
            approval_id, actor.org_id, for_update=True
        )
        if approval.status != ApprovalStatus.PENDING.value:
            raise InvalidStateError(f"Approval request already {approval.status}.")
        project_for_authz = self.projects.get_scoped(approval.project_id, actor.org_id)
        self.authz.require(actor, "approval.creative", project_for_authz)

        # Invariant 4: persist the human decision before resuming the graph.
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
                    "approved_scene_ids": list(approved_scene_ids) if approved_scene_ids is not None else None,
                    "approved_entity_ids": list(approved_entity_ids) if approved_entity_ids is not None else None,
                }
            ),
        )

        self.db.expire_all()
        project = self.projects.get_scoped(approval.project_id, actor.org_id)
        run = self.runs.get(run_id)
        return DecisionResult(
            approval_id=approval.id,
            decision=decision.value,
            run_status=run.status if run else WorkflowStatus.FAILED.value,
            new_project_version=project.current_version,
        )

    # -- internals -----------------------------------------------------------

    def _invoke(self, run_id: str, graph_input) -> None:
        config = {"configurable": {"thread_id": run_id}}
        try:
            with get_checkpointer() as checkpointer:
                graph = build_script_intelligence_graph().compile(checkpointer=checkpointer)
                graph.invoke(graph_input, config=config)
        except Exception as exc:
            logger.exception("Workflow run %s failed", run_id)
            self.db.rollback()
            self.runs.set_status(run_id, WorkflowStatus.FAILED.value, error_message=str(exc))
            self.db.commit()
            raise
