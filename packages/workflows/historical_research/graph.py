"""Historical Research LangGraph StateGraph (Workflow G-02).

investigate → propose candidates → human approval interrupt → commit | reject

Nodes orchestrate only. Canonical writes go through ``ResearchReviewService`` (ADR-001
invariant 2), and graph state carries references and compact candidate data.
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from packages.domain.enums import ApprovalDecision
from packages.domain.errors import ValidationFailure
from packages.persistence.database import session_scope
from packages.services.research_review import ResearchReviewService
from packages.workflows.historical_research.investigator import HistoricalInvestigator
from packages.workflows.historical_research.state import HistoricalResearchState


def investigate_node(state: HistoricalResearchState) -> dict[str, Any]:
    """Investigate the research topic and extract structured historical candidates."""
    topic = state.get("topic")
    if not topic or not topic.strip():
        raise ValidationFailure("Research topic cannot be empty.")

    claims, questions = HistoricalInvestigator().investigate(topic, state.get("seed_text"))
    return {"candidate_claims": claims, "candidate_questions": questions}


def generate_candidates_node(state: HistoricalResearchState) -> dict[str, Any]:
    """Persist extracted candidates and open a human approval request."""
    with session_scope() as db:
        proposed = ResearchReviewService(db).propose_candidates(
            state["workflow_run_id"],
            state.get("candidate_claims", []),
            state.get("candidate_questions", []),
            actor_id=state.get("actor_id"),
        )
    return {
        "approval_request_id": proposed.approval_request_id,
        "approval_status": "pending",
        "candidate_claims": proposed.claims,
        "candidate_questions": proposed.questions,
    }


def human_approval_interrupt_node(state: HistoricalResearchState) -> dict[str, Any]:
    """Pause until a reviewer decides. Resumed with ``Command(resume={...})``."""
    if state.get("approval_status", "pending") != "pending":
        return {}

    decision = interrupt(
        {
            "message": "Human approval required for Historical Research candidates",
            "approval_request_id": state.get("approval_request_id"),
        }
    )
    if not isinstance(decision, dict):
        decision = {}
    return {
        "approval_status": decision.get("decision", ApprovalDecision.REJECTED.value),
        "decision_notes": decision.get("notes"),
        "decided_by": decision.get("actor_id"),
        "approved_claim_ids": decision.get("approved_claim_ids"),
        "approved_question_ids": decision.get("approved_question_ids"),
    }


def route_decision(
    state: HistoricalResearchState,
) -> Literal["commit_canonical_node", "record_rejection_node"]:
    if state.get("approval_status") == ApprovalDecision.APPROVED.value:
        return "commit_canonical_node"
    return "record_rejection_node"


def commit_canonical_node(state: HistoricalResearchState) -> dict[str, Any]:
    """Promote approved candidates and advance the canonical project version."""
    actor_id = state.get("decided_by") or state["actor_id"]
    with session_scope() as db:
        new_version = ResearchReviewService(db).commit_approved_candidates(
            state["workflow_run_id"],
            decision_notes=state.get("decision_notes"),
            decided_by=actor_id,
            approved_claim_ids=state.get("approved_claim_ids"),
            approved_question_ids=state.get("approved_question_ids"),
        )
    return {"new_project_version": new_version, "completed": True}


def record_rejection_node(state: HistoricalResearchState) -> dict[str, Any]:
    """Close a rejected review without touching canonical state."""
    actor_id = state.get("decided_by") or state["actor_id"]
    with session_scope() as db:
        new_version = ResearchReviewService(db).reject_candidates(
            state["workflow_run_id"],
            notes=state.get("decision_notes"),
            actor_id=actor_id,
        )
    return {"new_project_version": new_version, "completed": True}


def build_historical_research_graph() -> StateGraph:
    """Build the (uncompiled) Historical Research StateGraph."""
    workflow = StateGraph(HistoricalResearchState)

    workflow.add_node("investigate_node", investigate_node)
    workflow.add_node("generate_candidates_node", generate_candidates_node)
    workflow.add_node("human_approval_interrupt_node", human_approval_interrupt_node)
    workflow.add_node("commit_canonical_node", commit_canonical_node)
    workflow.add_node("record_rejection_node", record_rejection_node)

    workflow.add_edge(START, "investigate_node")
    workflow.add_edge("investigate_node", "generate_candidates_node")
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

