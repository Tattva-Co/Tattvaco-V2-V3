"""Typed state for the Film Bible Synthesis workflow (Graph G-04 / WF-04).

In accordance with ADR-001 Invariant 6, state carries references and lightweight
structured candidate summaries, never raw heavy payloads or sensitive credentials.

Every key a node returns MUST be declared here: LangGraph silently drops undeclared
keys, which previously caused partial approvals to commit every rule (defect G04-A).
"""

from __future__ import annotations

from typing import Any, TypedDict


class FilmBibleState(TypedDict, total=False):
    # Identity & scoping
    workflow_run_id: str
    graph_id: str
    graph_version: str
    project_id: str
    organization_id: str
    actor_id: str  # initiator of the run; never overwritten by the reviewer
    expected_project_version: int  # version the run was started against; never overwritten

    # Inputs
    user_notes: str | None

    # Candidates
    candidate_rules: list[dict[str, Any]]

    # Approval gating
    approval_request_id: str | None
    approval_status: str  # pending, approved, rejected
    decision_notes: str | None
    decided_by: str | None
    approved_rule_ids: list[str] | None

    # Output & completion
    disposition: str | None
    new_project_version: int | None
    completed: bool
    error: str | None
