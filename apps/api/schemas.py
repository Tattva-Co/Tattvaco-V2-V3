"""Request/response contracts for the public API (``/api/v1``)."""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.enums import ApprovalDecision


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -- Authentication (development-only; see apps/api/routers/auth.py) --------


class DevLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    full_name: str = Field(default="Dev User", max_length=255)


class DevLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105  OAuth2 token-type field name, not a secret
    expires_in: int
    user_id: str
    organization_id: str


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
    # Read-only here: defaults to "fully_ai" at creation (DEC-021). Setting it is D1
    # scope (JRN-01.3 Production mode); GW1 only needs to report it so the journey UI
    # can explain why a mode-excluded group (e.g. JRN-07.4) shows not_applicable.
    production_mode: str
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
    scan_status: str
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
    # False (default, C6): queues the run for the background worker and returns
    # immediately with status="queued". True runs the graph inline in this request and
    # returns only once it reaches the approval interrupt or fails -- useful for a
    # synchronous caller (tests, a quick manual check), but ties up the request thread
    # for however long the graph takes, which does not scale past local/dev use.
    sync_execution: bool = False


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
    generator_mode: str
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
    generator_mode: str


class EntityCandidateResponse(_ORM):
    id: str
    workflow_run_id: str
    name: str
    category: str
    description: str | None
    confidence: float
    status: str
    generator_mode: str


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
    generator_mode: str


class ResearchQuestionCandidateResponse(_ORM):
    id: str
    workflow_run_id: str
    text: str
    category: str
    status: str
    generator_mode: str


class StoryboardPanelCandidateResponse(_ORM):
    id: str
    workflow_run_id: str
    panel_number: int
    suggested_scene_number: int | None
    shot_type: str
    description: str
    visual_notes: str | None
    dialogue_snippet: str | None
    confidence: float
    status: str
    generator_mode: str


class FilmBibleRuleCandidateResponse(_ORM):
    id: str
    workflow_run_id: str
    category: str
    title: str
    rule_text: str
    negative_prompt_guidance: str | None
    strictness: str
    suggested_claim_statement: str | None
    confidence: float
    conflict_warning: str | None
    status: str
    generator_mode: str


class ApprovalResponse(_ORM):
    id: str
    # Nullable since C8 (approval_requests.workflow_run_id widened so a future approval
    # can target something other than a workflow run's output); every row created by the
    # 4 existing graphs still has one -- this is forward compatibility, not a behaviour
    # change for anything that exists today.
    workflow_run_id: str | None
    target_type: str | None = None
    target_id: str | None = None
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
    storyboard_panels: List[StoryboardPanelCandidateResponse] = Field(default_factory=list)
    film_bible_rules: List[FilmBibleRuleCandidateResponse] = Field(default_factory=list)
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
    approved_panel_ids: List[str] | None = None
    approved_rule_ids: List[str] | None = None


class StoryboardPanelResponse(_ORM):
    id: str
    project_id: str
    project_version: int
    panel_number: int
    scene_id: str | None
    shot_type: str
    description: str
    visual_notes: str | None
    dialogue_snippet: str | None
    frame_asset_id: str | None
    aspect_ratio: str
    created_at: datetime


class StoryboardTriggerRequest(BaseModel):
    brief: str | None = None
    sync_execution: bool = False  # see WorkflowTriggerRequest; async by default (C6)


class FilmBibleRuleResponse(_ORM):
    id: str
    project_id: str
    project_version: int
    category: str
    title: str
    rule_text: str
    negative_prompt_guidance: str | None
    strictness: str
    historical_claim_id: str | None
    rationale: str | None
    created_at: datetime
    updated_at: datetime


class FilmBibleRuleCreateRequest(BaseModel):
    category: str = Field(..., max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    rule_text: str = Field(..., min_length=1)
    negative_prompt_guidance: str | None = None
    strictness: str = Field(default="guideline", max_length=50)
    historical_claim_id: str | None = None
    rationale: str | None = None


class FilmBibleTriggerRequest(BaseModel):
    user_notes: str | None = None
    sync_execution: bool = False  # see WorkflowTriggerRequest; async by default (C6)


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
    sync_execution: bool = False  # see WorkflowTriggerRequest; async by default (C6)


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


# -- Guided Workspace journey (GW1) ------------------------------------------


class JourneySubpointResponse(BaseModel):
    id: str
    key: str
    title: str
    kind: str
    description: str
    status: str
    not_applicable_reason: str | None = None
    evidence_refs: List[Any] = Field(default_factory=list)
    notes: str | None = None


class JourneyGroupResponse(BaseModel):
    id: str
    title: str
    purpose: str
    completion_rule: str
    required: bool
    na_policy: str
    release: str
    status: str
    applies: bool
    applicability_reason: str | None = None
    act_capability: str
    approval_capability: str | None = None
    can_act: bool
    can_approve: bool
    studio_tools: List[str]
    requirements: List[str]
    subpoints: List[JourneySubpointResponse]
    system_managed: bool = Field(
        default=False,
        description=(
            "True when this group's 'validate' subpoint is completed automatically by a "
            "system check (completion_check.kind == 'system') rather than by hand -- the "
            "client hides the manual 'Mark complete' action for that subpoint."
        ),
    )


class JourneySectionResponse(BaseModel):
    id: str
    title: str
    release_label: str
    status: str
    can_continue: bool
    groups: List[JourneyGroupResponse]


class JourneyItemActionRequest(BaseModel):
    action: str = Field(..., description="draft | complete | request_review | not_applicable")
    not_applicable_reason: str | None = None
    evidence_refs: List[Any] | None = None
    notes: str | None = None


class JourneySectionContinueResponse(BaseModel):
    section_id: str
    status: str
    group_statuses: Dict[str, str]
