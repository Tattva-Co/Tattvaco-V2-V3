"""Request/response contracts for the public API (``/api/v1``)."""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.enums import ApprovalDecision, ProductionMode, ProjectScale, QualityProfile


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
    # D1 (TFD-PRJ-001): only title is truly required. ``production_mode`` defaults to
    # ``mixed`` when omitted -- not the DB column's "fully_ai" migration-backfill
    # default (DEC-021), which exists only for rows created before this field was
    # settable -- so the legacy {title, logline, genre} body stays backward compatible
    # (AT-PRJ-001.3). The rest are "decide later" (null) until set (AT-PRJ-001.1).
    production_mode: ProductionMode | None = None
    format_template_key: str | None = None
    quality_profile: QualityProfile | None = None
    scale: ProjectScale | None = None


class ProjectUpdateRequest(BaseModel):
    """PATCH /projects/{id} (TFD-PRJ-002/003). Every field is optional; only fields
    actually present are changed (``exclude_unset`` at the service boundary), so
    omitting a field is not the same as explicitly clearing it."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    logline: str | None = None
    genre: str | None = Field(default=None, max_length=100)
    production_mode: ProductionMode | None = None
    format_template_key: str | None = None
    quality_profile: QualityProfile | None = None
    scale: ProjectScale | None = None


class ProjectResponse(_ORM):
    id: str
    organization_id: str
    title: str
    logline: str | None
    genre: str | None
    status: str
    production_mode: str
    format_template_key: str | None
    quality_profile: str | None
    scale: str | None
    current_version: int
    created_by: str
    created_at: datetime
    updated_at: datetime


# -- Format templates, output profiles, episodes (D1) ------------------------


class FormatTemplateResponse(BaseModel):
    key: str
    name: str
    structure_type: str
    required_workflow_steps: List[str]
    optional_workflow_steps: List[str]
    default_output_profile: Dict[str, Any]
    note: str | None = None


class OutputProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    resolution: str | None = None
    aspect_ratio: str | None = None
    fps: int | None = None
    duration_target_seconds: int | None = None
    audio_spec: str | None = None
    subtitles_required: bool = False
    delivery_format: str | None = None
    platform_notes: str | None = None
    is_default: bool = False


class OutputProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    resolution: str | None = None
    aspect_ratio: str | None = None
    fps: int | None = None
    duration_target_seconds: int | None = None
    audio_spec: str | None = None
    subtitles_required: bool | None = None
    delivery_format: str | None = None
    platform_notes: str | None = None
    is_default: bool | None = None


class OutputProfileResponse(_ORM):
    id: str
    project_id: str
    name: str
    resolution: str | None
    aspect_ratio: str | None
    fps: int | None
    duration_target_seconds: int | None
    audio_spec: str | None
    subtitles_required: bool
    delivery_format: str | None
    platform_notes: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class EpisodeCreateRequest(BaseModel):
    episode_number: int = Field(..., ge=1)
    title: str | None = Field(default=None, max_length=255)


class EpisodeResponse(_ORM):
    id: str
    project_id: str
    episode_number: int
    title: str | None
    created_at: datetime


# -- Project members & roles (D1, S-TEAM-02) ----------------------------------


class ProjectMemberAddRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    role_template_key: str = Field(..., min_length=1, max_length=50)


class ProjectMemberRoleUpdateRequest(BaseModel):
    role_template_key: str = Field(..., min_length=1, max_length=50)


class RoleTemplateResponse(BaseModel):
    key: str
    name: str
    capabilities: List[str]


class ProjectMemberResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role_template_key: str
    role_template_name: str
    capabilities: List[str]


# -- Project overview summary (D1, TFD-PRJ-007) -------------------------------


class RunningTaskSummary(BaseModel):
    workflow_run_id: str
    graph_id: str
    status: str
    created_at: datetime


class RecentChangeSummary(BaseModel):
    action: str
    actor_id: str
    target_type: str
    target_id: str
    created_at: datetime


class NextActionSummary(BaseModel):
    jrn_id: str
    title: str
    reason: str


class ProjectSummaryResponse(BaseModel):
    project_id: str
    project_version: int
    # Always null/"none_locked" until D2 adds screenplay_versions/is_production_canonical
    # -- an honest placeholder, not a stand-in computed from an unrelated table
    # (AT-PRJ-007 #1: no fabricated data).
    canonical_screenplay_version: int | None = None
    screenplay_lock_state: str = "none_locked"
    # Scene-level proxy for "mode distribution" (PRD's literal wording is shot-level,
    # which doesn't exist until D9): counts of canonical scenes by effective_mode.
    scene_count_by_effective_mode: Dict[str, int]
    pending_approvals_count: int
    # Always 0 until D10 adds continuity_findings -- the feature does not exist yet.
    unresolved_high_severity_findings_count: int = 0
    running_tasks: List[RunningTaskSummary]
    recent_changes: List[RecentChangeSummary]
    next_action: NextActionSummary | None


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
    # D2 (TFD-SCR-004): Script Intelligence reads a specific screenplay_version, never
    # an asset directly -- import it first (POST /screenplay-versions), then trigger
    # against the resulting version id.
    screenplay_version_id: str
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
    screenplay_version_id: str | None
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
    # D2 (TFD-SCR-009): which screenplay version this scene was extracted/committed
    # from; null for scenes committed before this column existed and never backfilled.
    screenplay_version_id: str | None
    # D2 (TFD-SCR-010): set by an impact analysis when the screenplay text this scene
    # came from was superseded by a locked revision that changed or removed it.
    review_status: str | None


class EntityResponse(_ORM):
    id: str
    name: str
    category: str
    description: str | None
    source_locator: str
    project_version: int
    review_status: str | None
    aliases: List[str]
    resolved_character_id: str | None
    resolved_location_id: str | None


# -- Story intelligence v2 (D3) -----------------------------------------------


class DialogueSegmentResponse(_ORM):
    id: str
    scene_id: str
    screenplay_version_id: str | None
    character_id: str | None
    character_name: str
    line_text: str
    parenthetical: str | None
    order_in_scene: int
    source_locator: str
    project_version: int
    created_at: datetime


class CharacterResponse(_ORM):
    id: str
    canonical_name: str
    aliases: List[str]
    project_version: int
    created_at: datetime


class LocationResponse(_ORM):
    id: str
    canonical_name: str
    aliases: List[str]
    project_version: int
    created_at: datetime


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


# -- Screenplay governance (D2) -----------------------------------------------


class ScreenplayVersionImportRequest(BaseModel):
    source_asset_id: str
    episode_id: str | None = None


class ScreenplayRevisionCreateRequest(BaseModel):
    base_version_id: str


class ScreenplayVersionUpdateRequest(BaseModel):
    content_text: str


class ScreenplaySubmitRequest(BaseModel):
    justification: str


class ScreenplayDecisionRequest(BaseModel):
    decision: ApprovalDecision
    notes: str | None = None


class ScreenplayDecisionResponse(BaseModel):
    approval_id: str
    decision: str
    version_status: str
    is_canonical: bool


class ScreenplayVersionResponse(_ORM):
    id: str
    project_id: str
    episode_id: str | None
    version_number: int
    status: str
    is_production_canonical: bool
    source_asset_id: str | None
    derived_from_version_id: str | None
    content_text: str
    content_hash: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    submitted_by: str | None
    locked_at: datetime | None
    locked_by: str | None


class ScreenplayDiffResponse(BaseModel):
    unified_diff: str
    scenes_changed: List[Dict[str, Any]]
    lines_added: int
    lines_removed: int


class ScreenplaySuggestionGenerateRequest(BaseModel):
    scope_notes: str | None = None


class ScreenplaySuggestionResponse(_ORM):
    id: str
    screenplay_version_id: str
    kind: str
    anchor: str
    suggestion_text: str
    rationale: str | None
    disposition: str
    disposition_notes: str | None
    decided_by: str | None
    decided_at: datetime | None
    generator_mode: str
    created_at: datetime


class ScreenplaySuggestionDecisionRequest(BaseModel):
    disposition: str = Field(..., description="accepted_for_revision | rejected | deferred")
    notes: str | None = None


class ImpactAnalysisResponse(_ORM):
    id: str
    project_id: str
    trigger_type: str
    new_version_id: str
    previous_version_id: str | None
    affected_items: List[Dict[str, Any]]
    created_by: str
    created_at: datetime


class ImpactPreviewResponse(BaseModel):
    affected_items: List[Dict[str, Any]]


# -- D4: Character & Digital Human (V1 foundation) ---------------------------------


class CharacterVersionResponse(_ORM):
    id: str
    character_id: str
    version_number: int
    status: str
    parent_version_id: str | None
    created_from: str
    approval_request_id: str | None
    approved_by: str | None
    approved_at: datetime | None
    identity_profile: Dict[str, Any]
    physical_profile: Dict[str, Any]
    created_by: str
    created_at: datetime


class CharacterDetailResponse(BaseModel):
    id: str
    canonical_name: str
    aliases: List[str]
    performer_id: str | None
    current_version: CharacterVersionResponse | None


class CharacterVersionProposeRequest(BaseModel):
    identity_patch: Dict[str, Any] | None = None
    physical_patch: Dict[str, Any] | None = None


class CharacterVersionProposeResponse(BaseModel):
    version: CharacterVersionResponse
    approval_request_id: str


class CharacterDecisionRequest(BaseModel):
    decision: ApprovalDecision
    notes: str | None = None


class CharacterFacialReferenceCreateRequest(BaseModel):
    asset_id: str
    role: str = Field(..., description="identity_front | identity_side | identity_three_quarter")
    facial_identity_version: int = 1


class CharacterFacialReferenceResponse(_ORM):
    id: str
    character_id: str
    asset_id: str
    role: str
    facial_identity_version: int
    consent_id: str | None
    created_by: str
    created_at: datetime


class CharacterStateCreateRequest(BaseModel):
    state_label: str = Field(..., min_length=1)
    applies_from_scene_id: str
    applies_until_scene_id: str | None = None
    deltas: Dict[str, Any] | None = None
    evidence_refs: List[Dict[str, Any]] | None = None


class CharacterStateResponse(_ORM):
    id: str
    character_id: str
    state_label: str
    applies_from_scene_id: str
    applies_until_scene_id: str | None
    deltas: Dict[str, Any]
    evidence_refs: List[Dict[str, Any]]
    status: str
    created_by: str
    created_at: datetime


class MeasurementCreateRequest(BaseModel):
    subject_type: str = Field(..., description="performer | character_version")
    subject_id: str
    measurement_key: str
    value: float
    unit: str | None = None
    capture_method: str
    confidence: float | None = None
    source_asset_id: str | None = None
    capture_device_or_tool: str | None = None
    notes: str | None = None


class MeasurementCorrectRequest(BaseModel):
    value: float
    unit: str | None = None
    notes: str | None = None


class MeasurementResponse(_ORM):
    id: str
    subject_type: str
    subject_id: str
    measurement_key: str
    value: float
    unit: str
    status: str
    confidence: float | None
    capture_method: str
    approved_by: str | None
    approved_at: datetime | None
    version: int
    capture_device_or_tool: str | None
    source_asset_id: str | None
    captured_at: datetime
    captured_by: str
    verified_by: str | None
    verified_at: datetime | None
    consent_id: str | None
    supersedes_id: str | None
    notes: str | None
    created_at: datetime


class PerformerCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)
    notes: str | None = None


class PerformerResponse(_ORM):
    id: str
    organization_id: str
    display_name: str
    notes: str | None
    created_by: str
    created_at: datetime


class ConsentCreateRequest(BaseModel):
    purpose: str
    project_scope: List[str] | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    document_asset_id: str | None = None
    template_version: str | None = None


class ConsentResponse(_ORM):
    id: str
    performer_id: str
    version: int
    supersedes_id: str | None
    purpose: str
    project_scope: List[str] | None
    status: str
    approval_request_id: str | None
    granted_at: datetime | None
    recorded_by: str
    approved_by: str | None
    revoked_at: datetime | None
    revoked_by: str | None
    revocation_reason: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    document_asset_id: str | None
    template_version: str | None
    created_at: datetime


class ConsentCreateResponse(BaseModel):
    consent: ConsentResponse
    approval_request_id: str


class ConsentDecisionRequest(BaseModel):
    decision: ApprovalDecision
    notes: str | None = None


class ConsentRevokeRequest(BaseModel):
    performer_id: str
    purpose: str
    reason: str | None = None


class ConsentCheckResponse(BaseModel):
    allowed: bool
    reason: str | None = None


class VoiceProfileCreateRequest(BaseModel):
    kind: str = Field(..., description="original_recording | clone | synthetic_voice | dubbing_voice")
    character_id: str | None = None
    performer_id: str | None = None


class VoiceProfileResponse(_ORM):
    id: str
    project_id: str
    character_id: str | None
    performer_id: str | None
    kind: str
    consent_id: str | None
    created_by: str
    created_at: datetime


# -- D5: Visual World ---------------------------------------------------------------


class LocationVersionResponse(_ORM):
    id: str
    location_id: str
    version_number: int
    status: str
    parent_version_id: str | None
    created_from: str
    approval_request_id: str | None
    approved_by: str | None
    approved_at: datetime | None
    profile: Dict[str, Any]
    created_by: str
    created_at: datetime


class LocationDetailResponse(BaseModel):
    id: str
    canonical_name: str
    aliases: List[str]
    current_version: LocationVersionResponse | None


class LocationVersionProposeRequest(BaseModel):
    profile_patch: Dict[str, Any] | None = None


class LocationVersionProposeResponse(BaseModel):
    version: LocationVersionResponse
    approval_request_id: str


class LocationDecisionRequest(BaseModel):
    decision: ApprovalDecision
    notes: str | None = None


class LocationAdoptResponse(BaseModel):
    matched_scene_ids: List[str]


class EnvironmentStateCreateRequest(BaseModel):
    scene_id: str
    location_id: str | None = None
    changes: Dict[str, Any]


class EnvironmentStateResponse(_ORM):
    id: str
    scene_id: str
    location_id: str | None
    changes: Dict[str, Any]
    status: str
    created_by: str
    created_at: datetime


class CostumeCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    character_id: str | None = None


class CostumeResponse(_ORM):
    id: str
    project_id: str
    name: str
    character_id: str | None
    current_version_id: str | None
    created_by: str
    created_at: datetime


class CostumeVersionResponse(_ORM):
    id: str
    costume_id: str
    version_number: int
    status: str
    parent_version_id: str | None
    created_from: str
    approval_request_id: str | None
    approved_by: str | None
    approved_at: datetime | None
    profile: Dict[str, Any]
    claim_links: List[str]
    created_by: str
    created_at: datetime


class CostumeDetailResponse(BaseModel):
    id: str
    name: str
    character_id: str | None
    current_version: CostumeVersionResponse | None


class CostumeVersionProposeRequest(BaseModel):
    profile_patch: Dict[str, Any] | None = None
    claim_links: List[str] | None = None


class CostumeVersionProposeResponse(BaseModel):
    version: CostumeVersionResponse
    approval_request_id: str


class CostumeDecisionRequest(BaseModel):
    decision: ApprovalDecision
    notes: str | None = None


class CostumeStateCreateRequest(BaseModel):
    state_label: str = Field(..., min_length=1)
    deltas: Dict[str, Any] | None = None


class CostumeStateResponse(_ORM):
    id: str
    costume_id: str
    state_label: str
    deltas: Dict[str, Any]
    status: str
    version: int
    supersedes_id: str | None
    created_by: str
    created_at: datetime


class CostumeAssignmentCreateRequest(BaseModel):
    character_id: str
    scene_id: str
    costume_id: str
    costume_state_id: str | None = None


class CostumeAssignmentResponse(_ORM):
    id: str
    character_id: str
    scene_id: str
    costume_id: str
    costume_state_id: str | None
    created_by: str
    created_at: datetime


class ContinuityFindingResponse(_ORM):
    id: str
    finding_type: str
    scene_id: str | None
    details: Dict[str, Any]
    status: str
    created_at: datetime


class PropCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    kind: str = Field(..., description="prop | weapon")
    type: str | None = None
    design: str | None = None
    material: str | None = None
    scale: str | None = None
    owner_character_id: str | None = None


class PropResponse(_ORM):
    id: str
    project_id: str
    name: str
    kind: str
    type: str | None
    design: str | None
    material: str | None
    scale: str | None
    owner_character_id: str | None
    created_by: str
    created_at: datetime


class PropStateCreateRequest(BaseModel):
    scene_id: str
    holder_character_id: str | None = None
    notes: str | None = None


class PropStateResponse(_ORM):
    id: str
    prop_id: str
    scene_id: str
    holder_character_id: str | None
    notes: str | None
    created_by: str
    created_at: datetime
