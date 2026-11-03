"""Tests verifying LangGraph checkpointing, pause/interrupt, and crash resumption."""

import uuid

import pytest
from langgraph.types import Command

from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    ApprovalRequestModel,
    AuditEventModel,
    ProjectModel,
    WorkflowRunModel,
)
from packages.workflows.checkpointer import get_checkpointer
from packages.workflows.script_intelligence.graph import build_script_intelligence_graph
from tests.support import SAMPLE_SCRIPT


@pytest.fixture
def run_context(tenant):
    proj_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    db = SessionLocal()
    db.add(
        ProjectModel(
            id=proj_id,
            organization_id=tenant.org_id,
            title="Test Film",
            current_version=1,
            created_by=tenant.user_id,
        )
    )
    db.flush()
    db.add(
        WorkflowRunModel(
            id=run_id,
            graph_id="script_intelligence",
            graph_version="1.0",
            project_id=proj_id,
            organization_id=tenant.org_id,
            actor_id=tenant.user_id,
            expected_project_version=1,
            status="running",
        )
    )
    db.commit()
    db.close()
    return {"org_id": tenant.org_id, "user_id": tenant.user_id, "proj_id": proj_id, "run_id": run_id}


def _initial_state(ctx):
    return {
        "workflow_run_id": ctx["run_id"],
        "project_id": ctx["proj_id"],
        "organization_id": ctx["org_id"],
        "actor_id": ctx["user_id"],
        "expected_project_version": 1,
        "script_asset_id": "asset-test",
        "raw_script_text": SAMPLE_SCRIPT,
        "approval_status": "pending",
    }


def test_langgraph_checkpoint_interrupt_and_resume(run_context):
    ctx = run_context
    config = {"configurable": {"thread_id": ctx["run_id"]}}

    # Phase 1: Run graph up to the human approval interrupt
    with get_checkpointer() as checkpointer:
        graph = build_script_intelligence_graph().compile(checkpointer=checkpointer)
        graph.invoke(_initial_state(ctx), config=config)
        state_after_interrupt = graph.get_state(config)
        assert len(state_after_interrupt.tasks) > 0  # paused on interrupt
        assert len(state_after_interrupt.values["extracted_scenes"]) == 2

    # Phase 2: Simulate process restart and resume with a human decision
    with get_checkpointer() as fresh_checkpointer:
        fresh_graph = build_script_intelligence_graph().compile(checkpointer=fresh_checkpointer)
        recovered_state = fresh_graph.get_state(config)
        assert recovered_state.values["workflow_run_id"] == ctx["run_id"]

        resume_command = Command(
            resume={
                "decision": "approved",
                "notes": "Verified historical accuracy",
                "actor_id": ctx["user_id"],
                "approved_scene_ids": None,  # None = approve every candidate
                "approved_entity_ids": None,
            }
        )
        res2 = fresh_graph.invoke(resume_command, config=config)
        assert res2["completed"] is True
        assert res2["new_project_version"] == 2

    # Phase 3: Verify canonical database state
    db = SessionLocal()
    try:
        proj = db.query(ProjectModel).filter_by(id=ctx["proj_id"]).one()
        assert proj.current_version == 2
        commit_audit = db.query(AuditEventModel).filter_by(
            project_id=ctx["proj_id"], action="script_intelligence_committed"
        ).one()
        assert commit_audit.target_id  # audit must reference the new version row
    finally:
        db.close()


def test_rejection_closes_approval_and_run_without_mutating_project(run_context):
    ctx = run_context
    config = {"configurable": {"thread_id": ctx["run_id"]}}

    with get_checkpointer() as checkpointer:
        graph = build_script_intelligence_graph().compile(checkpointer=checkpointer)
        graph.invoke(_initial_state(ctx), config=config)
        graph.invoke(
            Command(resume={"decision": "rejected", "notes": "Wrong draft", "actor_id": ctx["user_id"]}),
            config=config,
        )

    db = SessionLocal()
    try:
        approval = db.query(ApprovalRequestModel).filter_by(workflow_run_id=ctx["run_id"]).one()
        assert approval.status == "decided"
        assert approval.decision == "rejected"
        assert approval.decided_by == ctx["user_id"]

        run = db.query(WorkflowRunModel).filter_by(id=ctx["run_id"]).one()
        assert run.status == "rejected"

        proj = db.query(ProjectModel).filter_by(id=ctx["proj_id"]).one()
        assert proj.current_version == 1
    finally:
        db.close()
