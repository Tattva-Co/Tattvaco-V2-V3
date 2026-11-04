"""Typed state for the Historical Research workflow (Graph G-02).

In accordance with ADR-001 Invariant 6, state carries references and lightweight
structured candidate summaries, never raw heavy payloads or sensitive credentials.
"""

from __future__ import annotations

from typing import Any, TypedDict


class HistoricalResearchState(TypedDict, total=False):
    # Identity & scoping
    workflow_run_id: str
    graph_id: str
    graph_version: str
    project_id: str
    organization_id: str
    actor_id: str
    expected_project_version: int

    # Inputs
    topic: str
    seed_text: str | None

    # Extracted candidate references
    candidate_claims: list[dict[str, Any]]
    candidate_questions: list[dict[str, Any]]

    # Approval gating
    approval_request_id: str | None
    approval_status: str  # pending, approved, rejected
    decision_notes: str | None
    decided_by: str | None
    approved_claim_ids: list[str] | None
    approved_question_ids: list[str] | None

    # Output & completion
    new_project_version: int | None
    completed: bool

