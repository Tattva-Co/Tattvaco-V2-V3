"""State definition for the Script Intelligence (G-01) LangGraph workflow.

Checkpointed after every node, so keep it to references and compact candidate data.
"""

from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class ScriptIntelligenceState(TypedDict, total=False):
    # Context & tenant scoping
    workflow_run_id: str
    project_id: str
    organization_id: str
    actor_id: str
    expected_project_version: int

    # Inputs. ``raw_script_text`` is optional: when absent the parse node loads the
    # script from storage by ``script_asset_id`` (production path).
    script_asset_id: str
    raw_script_text: Optional[str]

    # Extracted candidate structures
    extracted_scenes: List[Dict[str, Any]]
    extracted_entities: List[Dict[str, Any]]

    # Approval gating. For the id lists, None = all candidates, [] = none.
    approval_request_id: Optional[str]
    approval_status: str  # pending, approved, rejected
    decision_notes: Optional[str]
    decided_by: Optional[str]
    approved_scene_ids: Optional[List[str]]
    approved_entity_ids: Optional[List[str]]

    # Output & completion
    new_project_version: Optional[int]
    completed: bool
