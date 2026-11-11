"""Storyboard Intelligence LangGraph StateGraph (Workflow G-03).

generate panels → propose candidates → human approval interrupt → commit | reject

Nodes orchestrate only. Canonical writes go through ``StoryboardReviewService`` (ADR-001
invariant 2), and graph state carries references and compact candidate data.
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from packages.ai.gateway import get_model_gateway
from packages.core.config import get_settings
from packages.domain.enums import ApprovalDecision
from packages.persistence.database import session_scope
from packages.persistence.repositories import CanonicalRepository
from packages.services.storyboard_review import StoryboardReviewService
from packages.workflows.storyboard_intelligence.state import StoryboardIntelligenceState


def generate_panels_node(state: StoryboardIntelligenceState) -> dict[str, Any]:
    """Generate storyboard panel candidates from canonical scenes or brief."""
    with session_scope() as db:
        scenes = CanonicalRepository(db).scenes_for_project(state["project_id"])
        scenes_data = [
            {
                "scene_number": s.scene_number,
                "heading": s.heading,
                "setting": s.setting,
                "summary": s.summary,
                "characters_present": s.characters_present,
            }
            for s in scenes
        ]
    result = get_model_gateway(get_settings()).align_storyboard(scenes_data, brief=state.get("brief"))
    return {"candidate_panels": [p.model_dump() for p in result.panels]}


def generate_candidates_node(state: StoryboardIntelligenceState) -> dict[str, Any]:
    """Persist generated panel candidates and open a human approval request."""
    with session_scope() as db:
        proposed = StoryboardReviewService(db).propose_candidates(
            state["workflow_run_id"],
            state.get("candidate_panels", []),
            actor_id=state.get("actor_id"),
        )
    return {
        "approval_request_id": proposed.approval_request_id,
        "approval_status": "pending",
        "candidate_panels": proposed.panels,
    }


def human_approval_interrupt_node(state: StoryboardIntelligenceState) -> dict[str, Any]:
    """Pause until a reviewer decides. Resumed with ``Command(resume={...})``."""
    if state.get("approval_status", "pending") != "pending":
        return {}

    decision = interrupt(
        {
            "message": "Human approval required for Storyboard Intelligence candidates",
            "approval_request_id": state.get("approval_request_id"),
        }
    )
    if not isinstance(decision, dict):
        decision = {}
    return {
        "approval_status": decision.get("decision", ApprovalDecision.REJECTED.value),
        "decision_notes": decision.get("notes"),
        "decided_by": decision.get("actor_id"),
        "approved_panel_ids": decision.get("approved_panel_ids"),
    }


def route_decision(
    state: StoryboardIntelligenceState,
) -> Literal["commit_canonical_node", "record_rejection_node"]:
    if state.get("approval_status") == ApprovalDecision.APPROVED.value:
        return "commit_canonical_node"
    return "record_rejection_node"


def commit_canonical_node(state: StoryboardIntelligenceState) -> dict[str, Any]:
    """Promote approved panel candidates and advance canonical project version."""
    actor_id = state.get("decided_by") or state["actor_id"]
    with session_scope() as db:
        new_version = StoryboardReviewService(db).commit_approved_candidates(
            state["workflow_run_id"],
            decision_notes=state.get("decision_notes"),
            decided_by=actor_id,
            approved_panel_ids=state.get("approved_panel_ids"),
        )
    return {"new_project_version": new_version, "completed": True}


def record_rejection_node(state: StoryboardIntelligenceState) -> dict[str, Any]:
    """Close a rejected review without touching canonical state."""
    actor_id = state.get("decided_by") or state["actor_id"]
    with session_scope() as db:
        new_version = StoryboardReviewService(db).reject_candidates(
            state["workflow_run_id"],
            notes=state.get("decision_notes"),
            actor_id=actor_id,
        )
    return {"new_project_version": new_version, "completed": True}


def build_storyboard_intelligence_graph() -> StateGraph:
    """Build the (uncompiled) Storyboard Intelligence StateGraph."""
    workflow = StateGraph(StoryboardIntelligenceState)

    workflow.add_node("generate_panels_node", generate_panels_node)
    workflow.add_node("generate_candidates_node", generate_candidates_node)
    workflow.add_node("human_approval_interrupt_node", human_approval_interrupt_node)
    workflow.add_node("commit_canonical_node", commit_canonical_node)
    workflow.add_node("record_rejection_node", record_rejection_node)

    workflow.add_edge(START, "generate_panels_node")
    workflow.add_edge("generate_panels_node", "generate_candidates_node")
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

