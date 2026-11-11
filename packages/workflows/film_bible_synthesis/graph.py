"""LangGraph workflow definition for Film Bible Synthesis (Workflow G-04).

Flow:
    synthesize_visual_rules -> human_approval_gate (interrupt) -> commit_rules | reject_rules -> END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from packages.ai.gateway import get_model_gateway
from packages.core.config import get_settings
from packages.core.logging import get_logger
from packages.domain.enums import ApprovalDecision
from packages.persistence.database import session_scope
from packages.persistence.repositories import CanonicalRepository, ResearchRepository
from packages.services.film_bible_review import FilmBibleReviewService
from packages.workflows.film_bible_synthesis.state import FilmBibleState

logger = get_logger("workflows.film_bible_synthesis")


def synthesize_visual_rules(state: FilmBibleState) -> dict[str, Any]:
    project_id = state["project_id"]
    run_id = state["workflow_run_id"]
    actor_id = state.get("actor_id")
    user_notes = state.get("user_notes")

    with session_scope() as db:
        scenes = [
            {
                "scene_number": s.scene_number,
                "heading": s.heading,
                "setting": s.setting,
                "location_name": s.location_name,
                "summary": s.summary,
                "characters_present": s.characters_present,
            }
            for s in CanonicalRepository(db).scenes_for_project(project_id)
        ]
        claims = [
            {
                "id": c.id,
                "claim_class": c.claim_class,
                "statement": c.statement,
                "era_or_date": c.era_or_date,
                "location": c.location,
            }
            for c in ResearchRepository(db).list_claims(project_id)
        ]

    result = get_model_gateway(get_settings()).synthesize_film_bible(scenes, claims, user_notes=user_notes)
    rules = [r.model_dump() for r in result.rules]

    with session_scope() as db:
        service = FilmBibleReviewService(db)
        proposed = service.propose_candidates(run_id, rules, actor_id=actor_id)

    return {
        "candidate_rules": proposed.rules,
        "approval_request_id": proposed.approval_request_id,
        "approval_status": "pending",
    }


def human_approval_gate(state: FilmBibleState) -> dict[str, Any]:
    """Pause until a reviewer decides. Resumed with ``Command(resume={...})``."""
    if state.get("approval_status", "pending") != "pending":
        return {}

    decision = interrupt(
        {
            "type": "film_bible_approval_required",
            "approval_request_id": state.get("approval_request_id"),
            "candidate_count": len(state.get("candidate_rules", [])),
        }
    )
    if not isinstance(decision, dict):
        decision = {}
    return {
        "approval_status": decision.get("decision", ApprovalDecision.REJECTED.value),
        "approved_rule_ids": decision.get("approved_rule_ids"),
        "decision_notes": decision.get("notes"),
        "decided_by": decision.get("actor_id"),
    }


def route_decision(state: FilmBibleState) -> str:
    status = state.get("approval_status")
    if status == ApprovalDecision.APPROVED.value:
        return "commit_rules"
    return "reject_rules"


def commit_rules(state: FilmBibleState) -> dict[str, Any]:
    """Promote approved rule candidates and advance the canonical project version."""
    run_id = state["workflow_run_id"]
    decided_by = state.get("decided_by") or state["actor_id"]

    with session_scope() as db:
        new_version = FilmBibleReviewService(db).commit_approved_candidates(
            run_id,
            state.get("decision_notes"),
            decided_by,
            approved_rule_ids=state.get("approved_rule_ids"),
        )

    logger.info("Film Bible committed for run %s, project at version v%s", run_id, new_version)
    return {"disposition": "approved", "new_project_version": new_version, "completed": True}


def reject_rules(state: FilmBibleState) -> dict[str, Any]:
    """Close a rejected review without touching canonical state."""
    run_id = state["workflow_run_id"]
    decided_by = state.get("decided_by") or state["actor_id"]

    with session_scope() as db:
        FilmBibleReviewService(db).reject_candidates(run_id, state.get("decision_notes"), decided_by)

    logger.info("Film Bible candidates rejected for run %s", run_id)
    return {"disposition": "rejected", "completed": True}


def build_film_bible_graph() -> StateGraph:
    builder = StateGraph(FilmBibleState)

    builder.add_node("synthesize_visual_rules", synthesize_visual_rules)
    builder.add_node("human_approval_gate", human_approval_gate)
    builder.add_node("commit_rules", commit_rules)
    builder.add_node("reject_rules", reject_rules)

    builder.add_edge(START, "synthesize_visual_rules")
    builder.add_edge("synthesize_visual_rules", "human_approval_gate")
    builder.add_conditional_edges(
        "human_approval_gate",
        route_decision,
        {
            "commit_rules": "commit_rules",
            "reject_rules": "reject_rules",
        },
    )
    builder.add_edge("commit_rules", END)
    builder.add_edge("reject_rules", END)

    return builder

