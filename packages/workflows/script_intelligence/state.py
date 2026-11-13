"""State definition for the Script Intelligence (G-01) LangGraph workflow.

Checkpointed after every node, so keep it to references and compact candidate data.
"""

from typing import Any, Dict, List

from typing_extensions import TypedDict


class ScriptIntelligenceState(TypedDict, total=False):
    # Context & tenant scoping
    workflow_run_id: str
    project_id: str
    organization_id: str
    actor_id: str
    expected_project_version: int

    # Input: the specific screenplay version to read (D2, TFD-SCR-004) -- never an
    # asset directly. The parse node reads screenplay_versions.content_text, already a
    # plain string snapshot; no storage/extraction lookup happens here anymore.
    screenplay_version_id: str

    # Extracted candidate structures
    extracted_scenes: List[Dict[str, Any]]
    extracted_entities: List[Dict[str, Any]]
    # D3 (TFD-STY-002): verbatim dialogue segments, keyed to a scene by scene_number
    # (scenes are not canonical yet at this point, so there is no scene_id to use).
    extracted_dialogue_segments: List[Dict[str, Any]]

    # Approval gating. For the id lists, None = all candidates, [] = none.
    approval_request_id: str | None
    approval_status: str  # pending, approved, rejected
    decision_notes: str | None
    decided_by: str | None
    approved_scene_ids: List[str] | None
    approved_entity_ids: List[str] | None

    # Output & completion
    new_project_version: int | None
    completed: bool
