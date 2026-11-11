"""Script Intelligence LangGraph StateGraph (Workflow G-01).

parse → propose candidates → human approval interrupt → commit | reject

Nodes orchestrate only. Canonical writes go through ``ScriptReviewService`` (ADR-001
invariant 2), and graph state carries references and compact candidate data, not the
script body (invariant 6) — the script is loaded from storage by asset id when parsed.
"""

from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from packages.ai.gateway import get_model_gateway
from packages.core.config import get_settings
from packages.domain.enums import ApprovalDecision
from packages.domain.errors import ValidationFailure
from packages.persistence.database import session_scope
from packages.services.script_review import RunScope, ScriptReviewService
from packages.storage.factory import get_storage
from packages.workflows.script_intelligence.state import ScriptIntelligenceState


def _scope(state: ScriptIntelligenceState) -> RunScope:
    return RunScope(
        run_id=state["workflow_run_id"],
        project_id=state["project_id"],
        org_id=state["organization_id"],
    )


def parse_script_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Parse the script into scene and entity candidates."""
    raw_text = state.get("raw_script_text")
    if raw_text is None:
        with session_scope() as db:
            raw_text = ScriptReviewService(db).load_script_text(state["script_asset_id"], get_storage())
    if not raw_text.strip():
        raise ValidationFailure("Script text is empty.")

    result = get_model_gateway(get_settings()).parse_screenplay(raw_text)
    return {
        "extracted_scenes": [s.model_dump() for s in result.scenes],
        "extracted_entities": [e.model_dump() for e in result.entities],
    }


def generate_candidates_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Persist extracted candidates and open a human approval request."""
    with session_scope() as db:
        proposed = ScriptReviewService(db).propose(
            _scope(state),
            state["actor_id"],
            state.get("extracted_scenes", []),
            state.get("extracted_entities", []),
        )
    return {
        "approval_request_id": proposed.approval_request_id,
        "approval_status": "pending",
        "extracted_scenes": proposed.scenes,
        "extracted_entities": proposed.entities,
    }


def human_approval_interrupt_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Pause until a reviewer decides. Resumed with ``Command(resume={...})``."""
    if state.get("approval_status", "pending") != "pending":
        return {}

    decision = interrupt(
        {
            "message": "Human approval required for Script Intelligence candidates",
            "approval_request_id": state.get("approval_request_id"),
        }
    )
    if not isinstance(decision, dict):
        decision = {}
    return {
        "approval_status": decision.get("decision", ApprovalDecision.REJECTED.value),
        "decision_notes": decision.get("notes"),
        "decided_by": decision.get("actor_id"),
        # None means "all candidates"; [] means "none".
        "approved_scene_ids": decision.get("approved_scene_ids"),
        "approved_entity_ids": decision.get("approved_entity_ids"),
    }


def route_decision(
    state: ScriptIntelligenceState,
) -> Literal["commit_canonical_node", "record_rejection_node"]:
    if state.get("approval_status") == ApprovalDecision.APPROVED.value:
        return "commit_canonical_node"
    return "record_rejection_node"


def commit_canonical_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Promote approved candidates and advance the canonical project version."""
    actor_id = state.get("decided_by") or state["actor_id"]
    with session_scope() as db:
        new_version = ScriptReviewService(db).promote_approved(
            _scope(state),
            actor_id,
            expected_version=state["expected_project_version"],
            approved_scene_ids=state.get("approved_scene_ids"),
            approved_entity_ids=state.get("approved_entity_ids"),
            notes=state.get("decision_notes"),
        )
    return {"new_project_version": new_version, "completed": True}


def record_rejection_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Close a rejected review without touching canonical state."""
    actor_id = state.get("decided_by") or state["actor_id"]
    with session_scope() as db:
        ScriptReviewService(db).close_rejected(_scope(state), actor_id, state.get("decision_notes"))
    return {"completed": True}


def build_script_intelligence_graph() -> StateGraph:
    """Build the (uncompiled) Script Intelligence StateGraph."""
    workflow = StateGraph(ScriptIntelligenceState)

    workflow.add_node("parse_script_node", parse_script_node)
    workflow.add_node("generate_candidates_node", generate_candidates_node)
    workflow.add_node("human_approval_interrupt_node", human_approval_interrupt_node)
    workflow.add_node("commit_canonical_node", commit_canonical_node)
    workflow.add_node("record_rejection_node", record_rejection_node)

    workflow.add_edge(START, "parse_script_node")
    workflow.add_edge("parse_script_node", "generate_candidates_node")
    workflow.add_edge("generate_candidates_node", "human_approval_interrupt_node")
    workflow.add_conditional_edges(
        "human_approval_interrupt_node",
        route_decision,
        {
            "commit_canonical_node": "commit_canonical_node",
            "record_rejection_node": "record_rejection_node",
        },
    )
    workflow.add_edge("commit_canonical_node", END)
    workflow.add_edge("record_rejection_node", END)

    return workflow
