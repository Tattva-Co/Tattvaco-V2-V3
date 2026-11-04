"""Request/response contracts for the public API (``/api/v1``)."""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.enums import ApprovalDecision


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -- Projects ---------------------------------------------------------------


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    logline: str | None = None
    genre: str | None = Field(default=None, max_length=100)


class ProjectResponse(_ORM):
    id: str
    organization_id: str
    title: str
    logline: str | None
    genre: str | None
    status: str
    current_version: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class ProjectVersionResponse(_ORM):
    id: str
    version_number: int
    branch_name: str
    commit_message: str
    committed_by: str
    snapshot_data: Dict[str, Any]
    created_at: datetime


class AuditEventResponse(_ORM):
    id: str
    action: str
    actor_id: str
    target_type: str
    target_id: str
    details: Dict[str, Any]
    created_at: datetime


# -- Assets -----------------------------------------------------------------


class AssetResponse(_ORM):
    id: str
    project_id: str
    filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    storage_path: str
    asset_type: str
    is_original: bool
    uploaded_by: str
    created_at: datetime


class AssetUploadResponse(BaseModel):
    asset_id: str
    filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    storage_path: str


# -- Workflows --------------------------------------------------------------


class WorkflowTriggerRequest(BaseModel):
    script_asset_id: str
    # True runs the graph inside the request (development convenience); False queues
    # the run for the background worker and returns immediately.
    sync_execution: bool = True


class WorkflowRunResponse(_ORM):
    id: str
    graph_id: str
    graph_version: str
    project_id: str
    status: str
    expected_project_version: int
    input_asset_ids: List[str]
    output_refs: Dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowTriggerResponse(BaseModel):
    workflow_run_id: str
    status: str
    approval_request_id: str | None = None
    candidate_summary: Dict[str, Any] = Field(default_factory=dict)


# -- Candidates & approvals -------------------------------------------------


class SceneCandidateResponse(_ORM):
    id: str
    workflow_run_id: str
    scene_number: int
    heading: str
    setting: str
    location_name: str
    time_of_day: str
    summary: str
    characters_present: List[str]
    status: str


class EntityCandidateResponse(_ORM):
    id: str
    workflow_run_id: str
    name: str
    category: str
    description: str | None
    confidence: float
    status: str


class ResearchClaimCandidateResponse(_ORM):
    id: str
    workflow_run_id: str
    claim_class: str
    statement: str
    era_or_date: str | None
    location: str | None
    confidence: float
    source_title: str
    source_tier: str
    source_locator: str | None
    status: str


class ResearchQuestionCandidateResponse(_ORM):
    id: str
    workflow_run_id: str
    text: str
    category: str
    status: str


class ApprovalResponse(_ORM):
    id: str
    workflow_run_id: str
    scope: str
    status: str
    decision: str | None
    decided_by: str | None
    decided_at: datetime | None
    candidate_summary: Dict[str, Any]


class CandidatesResponse(BaseModel):
    scenes: List[SceneCandidateResponse]
    entities: List[EntityCandidateResponse]
    research_claims: List[ResearchClaimCandidateResponse] = Field(default_factory=list)
    research_questions: List[ResearchQuestionCandidateResponse] = Field(default_factory=list)
    approvals: List[ApprovalResponse]


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision
    notes: str | None = None
    # Omit (null) to approve every candidate; send a list (possibly empty) to approve
    # exactly those candidates. Ignored for rejections.
    approved_scene_ids: List[str] | None = None
    approved_entity_ids: List[str] | None = None
    approved_claim_ids: List[str] | None = None
    approved_question_ids: List[str] | None = None


class ResearchQuestionCreateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    category: str = Field(default="general", max_length=50)


class ResearchQuestionResponse(_ORM):
    id: str
    project_id: str
    project_version: int
    text: str
    category: str
    status: str
    created_at: datetime
    updated_at: datetime


class ResearchSourceCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    tier: str = Field(default="tier_2_scholarly", max_length=50)
    author: str | None = None
    publication_year: int | None = None
    locator: str | None = None
    url: str | None = None
    asset_id: str | None = None
    reliability_notes: str | None = None


class ResearchSourceResponse(_ORM):
    id: str
    project_id: str
    project_version: int
    title: str
    tier: str
    author: str | None
    publication_year: int | None
    locator: str | None
    url: str | None
    asset_id: str | None
    reliability_notes: str | None
    created_at: datetime


class ResearchClaimResponse(_ORM):
    id: str
    project_id: str
    project_version: int
    claim_class: str
    statement: str
    era_or_date: str | None
    location: str | None
    confidence: float
    source_id: str | None
    question_id: str | None
    status: str
    created_at: datetime


class ResearchConflictResponse(_ORM):
    id: str
    project_id: str
    project_version: int
    claim_id_a: str
    claim_id_b: str
    description: str
    status: str
    resolution_notes: str | None
    created_at: datetime


class HistoricalResearchTriggerRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    seed_text: str | None = None
    sync_execution: bool = True


class ApprovalDecisionResponse(BaseModel):
    status: str = "decision_applied"
    approval_id: str
    decision: str
    run_status: str
    new_project_version: int


# -- Canonical film bible ---------------------------------------------------


class SceneResponse(_ORM):
    id: str
    scene_number: int
    heading: str
    setting: str
    location_name: str
    time_of_day: str
    summary: str
    source_locator: str
    characters_present: List[str]
    project_version: int


class EntityResponse(_ORM):
    id: str
    name: str
    category: str
    description: str | None
    source_locator: str
    project_version: int


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
