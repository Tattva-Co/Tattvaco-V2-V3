"""Tests verifying LangGraph checkpointing, pause/interrupt, and crash resumption."""

import uuid
import pytest
from langgraph.types import Command

from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    OrganizationModel,
    ProjectModel,
    UserModel,
    WorkflowRunModel,
)
from packages.workflows.checkpointer import get_checkpointer
from packages.workflows.script_intelligence.graph import build_script_intelligence_graph

SAMPLE_SCRIPT = """
EXT. RAJPUT FORTRESS - DAY

A fierce dust storm sweeps across the high ramparts.
RANA VEER (30s), clad in weathered armor, watches the distant valley.

RANA VEER
They arrive before dusk. Prepare the cavalry.

INT. WAR COUNCIL CHAMBER - NIGHT

Torches flicker against ancient stone walls.
BHAVANI (20s) unrolls a strategic parchment on the iron table.

BHAVANI
The northern pass is compromised. We hold the bridge.
"""


@pytest.fixture
def test_setup():
    db = SessionLocal()
    org_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    org = OrganizationModel(id=org_id, name="Test Studio", slug=f"test-{org_id[:8]}")
    user = UserModel(id=user_id, organization_id=org_id, email=f"{user_id[:8]}@test.com", full_name="Tester")
    proj = ProjectModel(id=proj_id, organization_id=org_id, title="Test Film", current_version=1, created_by=user_id)
    run = WorkflowRunModel(
        id=run_id,
        graph_id="script_intelligence",
        graph_version="1.0",
        project_id=proj_id,
        organization_id=org_id,
        actor_id=user_id,
        expected_project_version=1,
        status="running",
    )
    db.add(org)
    db.flush()
    db.add(user)
    db.flush()
    db.add(proj)
    db.flush()
    db.add(run)
    db.commit()
    db.close()

    yield {
        "org_id": org_id,
        "user_id": user_id,
        "proj_id": proj_id,
        "run_id": run_id,
    }

    # Cleanup
    db = SessionLocal()
    db.query(WorkflowRunModel).filter_by(id=run_id).delete()
    db.query(ProjectModel).filter_by(id=proj_id).delete()
    db.query(UserModel).filter_by(id=user_id).delete()
    db.query(OrganizationModel).filter_by(id=org_id).delete()
    db.commit()
    db.close()


def test_langgraph_checkpoint_interrupt_and_resume(test_setup):
    data = test_setup
    thread_id = data["run_id"]
    config = {"configurable": {"thread_id": thread_id}}

    # Phase 1: Run graph up to the human approval interrupt
    with get_checkpointer() as checkpointer:
        graph = build_script_intelligence_graph().compile(checkpointer=checkpointer)

        initial_state = {
            "workflow_run_id": data["run_id"],
            "project_id": data["proj_id"],
            "organization_id": data["org_id"],
            "actor_id": data["user_id"],
            "expected_project_version": 1,
            "script_asset_id": "asset-test",
            "raw_script_text": SAMPLE_SCRIPT,
            "approval_status": "pending",
        }

        # Invocation pauses at human_approval_interrupt_node
        res1 = graph.invoke(initial_state, config=config)
        state_after_interrupt = graph.get_state(config)
        assert len(state_after_interrupt.tasks) > 0  # Task is paused on interrupt
        assert state_after_interrupt.values["extracted_scenes"]
        assert len(state_after_interrupt.values["extracted_scenes"]) == 2

    # Phase 2: Simulate process shutdown/restart and resume with human approval decision
    with get_checkpointer() as fresh_checkpointer:
        fresh_graph = build_script_intelligence_graph().compile(checkpointer=fresh_checkpointer)

        # Check that state was durably persisted in PostgreSQL
        recovered_state = fresh_graph.get_state(config)
        assert recovered_state.values["workflow_run_id"] == data["run_id"]

        # Resume execution with human decision
        resume_command = Command(
            resume={
                "decision": "approved",
                "notes": "Verified historical accuracy",
                "actor_id": data["user_id"],
                "approved_scene_ids": [],  # Empty signifies approve all
                "approved_entity_ids": [],
            }
        )
        res2 = fresh_graph.invoke(resume_command, config=config)
        assert res2["completed"] is True
        assert res2["new_project_version"] == 2

    # Phase 3: Verify canonical database state
    db = SessionLocal()
    proj = db.query(ProjectModel).filter_by(id=data["proj_id"]).first()
    assert proj.current_version == 2
    db.close()
