"""State definition for the Script Intelligence (G-01) LangGraph workflow."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class ScriptIntelligenceState(TypedDict, total=False):
    # Context & Tenant scoping
    workflow_run_id: str
    project_id: str
    organization_id: str
    actor_id: str
    expected_project_version: int

    # Inputs
    script_asset_id: str
    raw_script_text: str

    # Extracted candidate structures
    extracted_scenes: List[Dict[str, Any]]
    extracted_entities: List[Dict[str, Any]]

    # Approval gating
    approval_request_id: Optional[str]
    approval_status: str  # pending, approved, rejected
    decision_notes: Optional[str]
    decided_by: Optional[str]
    approved_scene_ids: List[str]
    approved_entity_ids: List[str]

    # Output & Completion
    new_project_version: Optional[int]
    error_message: Optional[str]
    completed: bool
