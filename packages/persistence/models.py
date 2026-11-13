"""SQLAlchemy ORM models representing canonical entities, workflow runs, and audit logs."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    text,
)

from packages.persistence.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="creator", nullable=False)
    # External identity-provider linkage (ADR-003). Null for every user until an OIDC
    # login links this row by (idp_issuer, idp_subject) to the token's (iss, sub). Dev
    # tokens (environment=development) carry this users.id directly as `sub` and never
    # populate these columns — there is no external identity to record in that mode.
    idp_issuer = Column(String(255), nullable=True)
    idp_subject = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index(
            "uq_users_idp_identity",
            "idp_issuer",
            "idp_subject",
            unique=True,
            postgresql_where=idp_issuer.isnot(None),
        ),
    )


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    logline = Column(Text, nullable=True)
    genre = Column(String(100), nullable=True)
    status = Column(String(50), default="draft", nullable=False)
    # One of packages.domain.journey_manifest.yaml enums.production_modes
    # (fully_ai | hybrid_live_action | mixed). Minimal pull-forward of D1's production
    # mode field (TFD-PRJ-003..006): the journey engine's applicability resolver (GW1)
    # cannot function without it. DEC-021: existing projects backfill to "fully_ai".
    # D1 owns the rest of the format/mode UI and any per-sequence/scene/shot override.
    production_mode = Column(String(50), default="fully_ai", nullable=False)
    # D1 (TFD-PRJ-001): "decide later" fields -- null until the owner sets them, and
    # required only before shot packaging (D11), not at creation (AT-PRJ-001.1).
    # format_template_key references packages.domain.format_templates.FORMAT_TEMPLATES_BY_KEY
    # (configuration data, not a DB table/FK -- see that module's docstring).
    format_template_key = Column(String(50), nullable=True)
    quality_profile = Column(String(50), nullable=True)  # packages.domain.enums.QualityProfile
    scale = Column(String(50), nullable=True)  # packages.domain.enums.ProjectScale
    current_version = Column(Integer, default=1, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ProjectVersionModel(Base):
    __tablename__ = "project_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    branch_name = Column(String(100), default="main", nullable=False)
    commit_message = Column(Text, nullable=False)
    committed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    snapshot_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # TFD-VER-001: one row per (project, version number). The row lock taken before every
    # version bump (C4) prevents the race; this makes a duplicate impossible at the DB level.
    __table_args__ = (Index("uq_project_versions_project_number", "project_id", "version_number", unique=True),)


class EpisodeModel(Base):
    """One episode of an episodic-structure project (D1, TFD-FMT-003). Only meaningful
    for projects whose format_template_key has structure_type="episodic"
    (packages.domain.format_templates); a linear-structure project has none."""

    __tablename__ = "episodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    episode_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (Index("uq_episodes_project_number", "project_id", "episode_number", unique=True),)


class OutputProfileModel(Base):
    """A delivery/output profile (D1, TFD-FMT-002): resolution, aspect ratio, frame
    rate, duration target, audio, subtitles, delivery format and platform notes. A
    project has one or more; ``is_default`` marks the one shot/post handoff packaging
    (D11) falls back to when a shot does not name one explicitly."""

    __tablename__ = "output_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    resolution = Column(String(50), nullable=True)
    aspect_ratio = Column(String(20), nullable=True)
    fps = Column(Integer, nullable=True)
    duration_target_seconds = Column(Integer, nullable=True)
    audio_spec = Column(String(100), nullable=True)
    subtitles_required = Column(Boolean, default=False, nullable=False)
    delivery_format = Column(String(100), nullable=True)
    platform_notes = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AssetModel(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    # BigInteger: a plain Integer overflows at ~2.1 GB, which would reject legitimate
    # video/footage uploads outright once media ingestion lands (docs/audit/05 §2).
    size_bytes = Column(BigInteger, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    storage_path = Column(String(512), nullable=False)
    asset_type = Column(String(50), default="script", nullable=False)
    is_original = Column(Boolean, default=True, nullable=False)
    parent_asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    asset_metadata = Column("metadata", JSON, default=dict, nullable=False)
    # Malware-scan lifecycle (C7; packages.domain.enums.AssetScanStatus). No workflow may
    # read an asset's content before this is "clean" (packages/services/scanning.py).
    scan_status = Column(String(20), nullable=False)
    scanned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssetDerivativeModel(Base):
    """Extracted plain text from a non-plain-text asset (PDF, DOCX, Final Draft .fdx;
    C7, packages/services/extraction.py). One row per (asset, derivative_type): a
    re-extraction overwrites rather than appends (see AssetService.upload_stream)."""

    __tablename__ = "asset_derivatives"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    derivative_type = Column(String(50), nullable=False)
    extractor = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    extraction_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("uq_asset_derivatives_asset_type", "asset_id", "derivative_type", unique=True),
    )


# -- Screenplay governance (D2; PRD §3, docs/product/ACCEPTANCE_CRITERIA.md §3.5) ----


class ScreenplayVersionModel(Base):
    """One screenplay text snapshot (PRD §3.1's state machine: draft -> in_review ->
    approved_locked -> superseded, or in_review -> rejected / back to draft). A revision
    is a new row (``derived_from_version_id`` set), never an edit of an existing locked
    row -- TFD-SCR-003's immutability invariant holds by construction once a row leaves
    ``draft``: every content-mutating path checks ``status == draft`` first."""

    __tablename__ = "screenplay_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    # D1's episodic-structure foundation (TFD-SCR-011): null for a linear-structure
    # project; one independent version lineage and one canonical slot per episode
    # otherwise -- see the partial unique index below.
    episode_id = Column(String(36), ForeignKey("episodes.id"), nullable=True, index=True)
    version_number = Column(Integer, nullable=False)
    status = Column(String(50), default="draft", nullable=False)  # packages.domain.enums.ScreenplayVersionStatus
    is_production_canonical = Column(Boolean, default=False, nullable=False)
    # The asset this version was imported from (TFD-SCR-001). Null for a revision
    # derived from another version rather than imported fresh from a file.
    source_asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True)
    derived_from_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=True)
    content_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)  # sha256 hex digest of content_text
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submitted_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        # postgresql_nulls_not_distinct (PG15+): without it, Postgres's default
        # NULLS DISTINCT means two rows that both have episode_id=NULL (every
        # linear-structure, i.e. non-episodic, project) are NEVER considered duplicates
        # by a unique index no matter what else matches -- silently defeating both
        # constraints below for the common case. NOT NULL episode_id (episodic
        # projects) was never affected; this only restores the intended behavior for
        # episode_id IS NULL.
        Index(
            "uq_screenplay_versions_project_number",
            "project_id",
            "episode_id",
            "version_number",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        # TFD-SCR-002/AT-SCR-002.2: a DB-level guarantee, not just an app-level check --
        # two concurrent "approve" transactions for the same (project, episode) can't
        # both commit a canonical row; the second's INSERT/UPDATE hits this constraint
        # and the service maps that into a 409, never two canonical versions at once.
        Index(
            "uq_screenplay_versions_one_canonical",
            "project_id",
            "episode_id",
            unique=True,
            postgresql_where=text("is_production_canonical = true"),
            postgresql_nulls_not_distinct=True,
        ),
    )


class ScreenplaySuggestionModel(Base):
    """An AI-proposed creative suggestion (TFD-SCR-005, Workflow 2 in PRD §3 -- the AI
    may propose but never edit the screenplay itself). Disposition is a plain status
    write with no promotion step: an accepted suggestion is available for a Director to
    manually incorporate into a revision's ``content_text``, never auto-applied."""

    __tablename__ = "screenplay_suggestions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    screenplay_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    kind = Column(String(50), nullable=False)  # packages.domain.enums.SuggestionKind
    anchor = Column(String(100), nullable=False)  # e.g. "Scene 12" -- scene/line locator
    suggestion_text = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    disposition = Column(String(50), default="pending", nullable=False)
    disposition_notes = Column(Text, nullable=True)
    decided_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    # C10: which ModelGateway produced this suggestion (packages.ai.gateway GENERATOR_MODE_*).
    generator_mode = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ScreenplayChangeModel(Base):
    """One "submit for review" event on a revision (TFD-SCR-006/008): the computed diff
    against its base version and the Director's required justification. A revision
    bounced back with "changes requested" and resubmitted gets a second row here, so the
    full history of every submission attempt is retained, not just the latest."""

    __tablename__ = "screenplay_changes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    screenplay_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    diffed_against_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=False)
    diff_summary = Column(JSON, nullable=False)  # {"unified_diff": str, "scenes_changed": [...], ...}
    justification = Column(Text, nullable=False)
    submitted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ImpactAnalysisModel(Base):
    """TFD-SCR-010 (PRD §3.1 invariant 4): computed when a revision is locked, listing
    every canonical item whose source screenplay text changed or disappeared. Nothing
    else happens automatically -- affected rows are flagged (see SceneModel/EntityModel
    .review_status) for a human to review, never edited or deleted by this process."""

    __tablename__ = "impact_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    trigger_type = Column(String(50), nullable=False)  # e.g. "screenplay_lock"
    new_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=False)
    previous_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=True)
    affected_items = Column(JSON, default=list, nullable=False)  # [{"item_type", "item_id", "reason"}, ...]
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    graph_id = Column(String(50), nullable=False)
    graph_version = Column(String(20), default="1.0", nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    expected_project_version = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)
    input_asset_ids = Column(JSON, default=list, nullable=False)
    output_refs = Column(JSON, default=dict, nullable=False)
    error_message = Column(Text, nullable=True)
    # C10: which ModelGateway produced this run's candidates (packages.ai.gateway
    # GENERATOR_MODE_*) -- "the mode is visible in the UI" exit criterion.
    generator_mode = Column(String(20), nullable=False)
    # D2 (TFD-SCR-004/009): the specific screenplay_version Script Intelligence (WF-01)
    # read from. Null for every other graph (historical research, storyboard, film
    # bible), which have no screenplay-version concept. Read back by
    # ScriptReviewService.promote_approved to stamp newly-promoted scenes with it --
    # the same "metadata lives on the run, not threaded through candidates/state"
    # pattern C10's generator_mode established (DEC-040).
    screenplay_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class OutboxTaskModel(Base):
    """PostgreSQL-backed durable outbox for worker dispatching.

    Lease/retry/dead-letter fields (C6; docs/audit/08 PERF-04): a CLAIMED task whose
    ``lease_expires_at`` has passed is treated as abandoned by a crashed worker and is
    reclaimable by any worker, with no separate sweep process -- ``claim_next`` just
    looks for either a due PENDING task or an expired-lease CLAIMED one. A failed attempt
    returns to PENDING with a future ``next_attempt_at`` (exponential backoff with
    jitter) until ``attempts`` reaches ``max_attempts``, at which point it is marked
    DEAD_LETTERED and never reclaimed again.
    """
    __tablename__ = "outbox_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    # Not unique (C6): a run may get a new task after an earlier one completes or is
    # dead-lettered. At most one *active* (pending or claimed) task per run is still
    # enforced by uq_outbox_tasks_active_run below, so a run can't be dispatched twice.
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    task_type = Column(String(100), nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    # pending, claimed, completed, dead_lettered (legacy rows may still say "failed")
    status = Column(String(50), default="pending", nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    claimed_by = Column(String(100), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_error_class = Column(String(255), nullable=True)
    last_error_message = Column(Text, nullable=True)
    dead_lettered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index(
            "uq_outbox_tasks_active_run",
            "workflow_run_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'claimed')"),
        ),
    )


class ApprovalRequestModel(Base):
    """Every approval to date originates from one of the 4 graphs' candidate-review gate
    (`workflow_run_id`, `scope`, `candidate_summary`). C8 widens the table so a FUTURE
    approval needn't originate from a workflow run at all -- e.g. D2's screenplay-lock
    decision, which approves a director's manual revision, not a graph's output.
    `workflow_run_id` becomes nullable; `target_type`/`target_id` are the generic
    alternative a non-workflow-run approval would use instead. Nothing creates one of
    those yet (every row today still has `workflow_run_id` set and `target_type` NULL) --
    the routing logic in apps/api/routers/approvals.py stays scope-based until D2 actually
    defines what a non-workflow approval's decision path looks like, rather than guessing
    it now with no real consumer to validate against."""

    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=True, index=True)
    target_type = Column(String(100), nullable=True)
    target_id = Column(String(36), nullable=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    scope = Column(String(100), default="script_intelligence_candidates", nullable=False)
    candidate_summary = Column(JSON, default=dict, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)
    decision = Column(String(50), nullable=True)
    decision_notes = Column(Text, nullable=True)
    decided_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    target_id = Column(String(36), nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# -- Story intelligence v2 (D3; PRD TFD-STY-002/003) -------------------------------


class CharacterModel(Base):
    """A resolved character identity (TFD-STY-003): one row per distinct character in
    a project, deduplicated from however many raw cue variants (``entities`` rows,
    ``entity_candidates.aliases``) referred to them across however many Script
    Intelligence runs. ``entities.resolved_character_id`` links the legacy rows back
    here -- the many-to-one direction, since one character can accumulate several
    legacy entity rows over time (one per run/version that mentioned them)."""

    __tablename__ = "characters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    canonical_name = Column(String(255), nullable=False)
    aliases = Column(JSON, default=list, nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("uq_characters_project_name", "project_id", "canonical_name", unique=True),)


class LocationModel(Base):
    """A resolved location identity (TFD-STY-003). See CharacterModel -- same shape,
    same resolve-at-promotion-time and legacy-link pattern, applied to the other
    entity category TFD-STY-003 names."""

    __tablename__ = "locations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    canonical_name = Column(String(255), nullable=False)
    aliases = Column(JSON, default=list, nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("uq_locations_project_name", "project_id", "canonical_name", unique=True),)


class DialogueSegmentCandidateModel(Base):
    """Extracted verbatim dialogue segments pending human approval (TFD-STY-002). Keyed
    to a scene by ``scene_number`` rather than an FK -- the scene candidate it belongs
    to is not canonical yet either, so there is no ``scene_id`` to point to until both
    are promoted together."""

    __tablename__ = "dialogue_segment_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    scene_number = Column(Integer, nullable=False)
    character_name = Column(String(255), nullable=False)
    line_text = Column(Text, nullable=False)
    parenthetical = Column(Text, nullable=True)
    order_in_scene = Column(Integer, nullable=False)
    source_locator = Column(String(100), nullable=False)
    status = Column(String(50), default="proposed", nullable=False)
    generator_mode = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class DialogueSegmentModel(Base):
    """Canonical verbatim dialogue (TFD-STY-002). Immutable once written -- no service
    method ever updates a row here (AT-STY-002.2: "a canonical dialogue segment is
    never mutated by any API"); a later revision's re-extraction simply adds new rows
    at a new ``project_version``, the same pattern scenes/entities already follow."""

    __tablename__ = "dialogue_segments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    scene_id = Column(String(36), ForeignKey("scenes.id"), nullable=False, index=True)
    screenplay_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=True)
    character_id = Column(String(36), ForeignKey("characters.id"), nullable=True)
    character_name = Column(String(255), nullable=False)
    line_text = Column(Text, nullable=False)
    parenthetical = Column(Text, nullable=True)
    order_in_scene = Column(Integer, nullable=False)
    source_locator = Column(String(100), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SceneCandidateModel(Base):
    """Extracted scene candidates pending human approval."""
    __tablename__ = "scene_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    scene_number = Column(Integer, nullable=False)
    heading = Column(String(255), nullable=False)
    setting = Column(String(10), default="EXT", nullable=False)
    location_name = Column(String(255), nullable=False)
    time_of_day = Column(String(50), default="DAY", nullable=False)
    summary = Column(Text, nullable=False)
    source_locator = Column(String(100), nullable=False)
    characters_present = Column(JSON, default=list, nullable=False)
    status = Column(String(50), default="proposed", nullable=False)  # proposed, approved, rejected
    # C10: which ModelGateway produced this candidate (packages.ai.gateway GENERATOR_MODE_*).
    generator_mode = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class EntityCandidateModel(Base):
    """Extracted entity candidates (characters, props, locations) pending human approval."""
    __tablename__ = "entity_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), default="character", nullable=False)
    description = Column(Text, nullable=True)
    source_locator = Column(String(100), nullable=False)
    confidence = Column(Float, default=0.9, nullable=False)
    status = Column(String(50), default="proposed", nullable=False)  # proposed, approved, rejected
    generator_mode = Column(String(20), nullable=False)
    # D3 (TFD-STY-003): raw cue/name variants the parser folded into this one
    # candidate (e.g. every distinct way a character's name appeared in the script).
    aliases = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SceneModel(Base):
    """Canonical approved scenes in the project."""
    __tablename__ = "scenes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    scene_number = Column(Integer, nullable=False)
    heading = Column(String(255), nullable=False)
    setting = Column(String(10), nullable=False)
    location_name = Column(String(255), nullable=False)
    time_of_day = Column(String(50), nullable=False)
    summary = Column(Text, nullable=False)
    source_locator = Column(String(100), nullable=False)
    characters_present = Column(JSON, default=list, nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    # D1 (TFD-PRJ-004): nullable mode override -- null means "inherit the project's
    # production_mode". effective_mode(scene) = scene.production_mode ?? project.production_mode
    # (PRD §2.2). Sequence/character/shot-level overrides are added when those tables
    # exist (D9/D5/D9 respectively; roadmap D1 row).
    production_mode = Column(String(50), nullable=True)
    # D1 (TFD-FMT-003): which episode this scene belongs to, for episodic formats only
    # (null for linear-structure projects). Nullable, not yet consumed by any scene-list
    # filter -- Script Intelligence does not assign an episode when parsing (that wiring
    # is D2/D3's screenplay-governance concern); this column exists now so D2/D3 need no
    # second migration to add it.
    episode_id = Column(String(36), ForeignKey("episodes.id"), nullable=True, index=True)
    # D2 (TFD-SCR-009): which screenplay version this scene was extracted/committed
    # from. Set once at promotion time and never retargeted when a newer version is
    # locked (AT-SCR-009.1: "existing items still show v3 until re-anchored"). Nullable
    # because every scene that predates this column has no real version to point at
    # (backfilled by the same migration that creates each project's v1 screenplay_version).
    screenplay_version_id = Column(String(36), ForeignKey("screenplay_versions.id"), nullable=True, index=True)
    # D2 (TFD-SCR-010): set to packages.domain.enums.REVIEW_STATUS_REQUIRED by an impact
    # analysis when the screenplay version this scene came from was superseded by a
    # locked revision that changed or removed it. Null = no outstanding review. Nothing
    # else about the row changes when this is set ("nothing propagates automatically").
    review_status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class EntityModel(Base):
    """Canonical approved entities (characters, locations, props)."""
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    source_locator = Column(String(100), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    # D2 (TFD-SCR-010): see SceneModel.review_status -- entities (characters) are the
    # other canonical item type an impact analysis can flag, per PRD §3.1 invariant 4
    # ("lists affected scenes, characters...").
    review_status = Column(String(50), nullable=True)
    aliases = Column(JSON, default=list, nullable=False)
    # D3 (TFD-STY-003): "on approval, a characters/locations row is created, linked to
    # any matching legacy entities row" -- set at promotion time depending on
    # ``category``; exactly one of the two is ever non-null for a given row.
    resolved_character_id = Column(String(36), ForeignKey("characters.id"), nullable=True)
    resolved_location_id = Column(String(36), ForeignKey("locations.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ResearchQuestionModel(Base):
    """Canonical open questions guiding historical and cultural research."""
    __tablename__ = "research_questions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    text = Column(Text, nullable=False)
    category = Column(String(50), default="general", nullable=False)
    status = Column(String(50), default="open", nullable=False)  # open, investigating, resolved, deferred
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ResearchSourceModel(Base):
    """Canonical bibliographic/archival source references with tier classification."""
    __tablename__ = "research_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    title = Column(String(255), nullable=False)
    tier = Column(String(50), default="tier_2_scholarly", nullable=False)
    author = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True)
    locator = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True)
    reliability_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ResearchClaimModel(Base):
    """Canonical evidence-backed claims and interpretations committed to project version."""
    __tablename__ = "research_claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    claim_class = Column(String(50), default="historical_fact", nullable=False)
    statement = Column(Text, nullable=False)
    era_or_date = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    source_id = Column(String(36), ForeignKey("research_sources.id"), nullable=True)
    question_id = Column(String(36), ForeignKey("research_questions.id"), nullable=True)
    status = Column(String(50), default="approved", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ResearchConflictModel(Base):
    """Contradictions or contested evidence between two claims."""
    __tablename__ = "research_conflicts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    claim_id_a = Column(String(36), ForeignKey("research_claims.id"), nullable=False)
    claim_id_b = Column(String(36), ForeignKey("research_claims.id"), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="open", nullable=False)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ResearchClaimCandidateModel(Base):
    """AI-proposed research claims awaiting human review."""
    __tablename__ = "research_claim_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    claim_class = Column(String(50), default="historical_fact", nullable=False)
    statement = Column(Text, nullable=False)
    era_or_date = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    confidence = Column(Float, default=0.9, nullable=False)
    source_title = Column(String(255), nullable=False)
    source_tier = Column(String(50), default="tier_2_scholarly", nullable=False)
    source_locator = Column(String(255), nullable=True)
    status = Column(String(50), default="proposed", nullable=False)  # proposed, approved, rejected
    generator_mode = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ResearchQuestionCandidateModel(Base):
    """AI-proposed open questions awaiting human review."""
    __tablename__ = "research_question_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    text = Column(Text, nullable=False)
    category = Column(String(50), default="general", nullable=False)
    status = Column(String(50), default="proposed", nullable=False)  # proposed, approved, rejected
    generator_mode = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class StoryboardPanelModel(Base):
    """Canonical approved storyboard panels aligned to scenes."""
    __tablename__ = "storyboard_panels"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    panel_number = Column(Integer, nullable=False)
    scene_id = Column(String(36), ForeignKey("scenes.id"), nullable=True, index=True)
    shot_type = Column(String(50), default="wide", nullable=False)
    description = Column(Text, nullable=False)
    visual_notes = Column(Text, nullable=True)
    dialogue_snippet = Column(Text, nullable=True)
    frame_asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True)
    aspect_ratio = Column(String(20), default="16:9", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class StoryboardPanelCandidateModel(Base):
    """AI-proposed storyboard panels awaiting director approval."""
    __tablename__ = "storyboard_panel_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    panel_number = Column(Integer, nullable=False)
    suggested_scene_number = Column(Integer, nullable=True)
    shot_type = Column(String(50), default="wide", nullable=False)
    description = Column(Text, nullable=False)
    visual_notes = Column(Text, nullable=True)
    dialogue_snippet = Column(Text, nullable=True)
    confidence = Column(Float, default=0.9, nullable=False)
    status = Column(String(50), default="proposed", nullable=False)  # proposed, approved, rejected
    generator_mode = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class FilmBibleRuleModel(Base):
    """Canonical visual world rules and creative guidelines (Workflow G-04)."""
    __tablename__ = "film_bible_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    rule_text = Column(Text, nullable=False)
    negative_prompt_guidance = Column(Text, nullable=True)
    strictness = Column(String(50), default="guideline", nullable=False)
    historical_claim_id = Column(String(36), ForeignKey("research_claims.id"), nullable=True, index=True)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class FilmBibleRuleCandidateModel(Base):
    """AI-synthesized visual world rule candidates awaiting director approval."""
    __tablename__ = "film_bible_rule_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    rule_text = Column(Text, nullable=False)
    negative_prompt_guidance = Column(Text, nullable=True)
    strictness = Column(String(50), default="guideline", nullable=False)
    suggested_claim_statement = Column(Text, nullable=True)
    confidence = Column(Float, default=0.9, nullable=False)
    conflict_warning = Column(Text, nullable=True)
    status = Column(String(50), default="proposed", nullable=False)
    generator_mode = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# -- Authorization (ADR-003 §2) ----------------------------------------------
#
# Enforcement lives in packages/services/authz.py::AuthzService, reading these tables
# through MembershipRepository/RoleTemplateRepository/ProjectMembershipRepository. The
# capability catalogue and default per-role bundles are the single source of truth in
# packages/domain/capabilities.py; this schema only stores assignments.


class MembershipModel(Base):
    """Org-level membership. An org_role of 'owner' holds every capability on every
    project in that org implicitly (AuthzService never consults project_memberships for
    an owner); 'admin'/'member' are not yet distinguished beyond that bypass."""
    __tablename__ = "memberships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    org_role = Column(String(50), default="member", nullable=False)
    status = Column(String(50), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("uq_memberships_user_org", "user_id", "organization_id", unique=True),)


class RoleTemplateModel(Base):
    """A named, editable bundle of capabilities, seeded per organization so each org can
    later customize its own templates without affecting any other tenant."""
    __tablename__ = "role_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    key = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    is_system = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("uq_role_templates_org_key", "organization_id", "key", unique=True),)


class CapabilityModel(Base):
    """Static reference table mirroring packages.domain.capabilities.CAPABILITIES."""
    __tablename__ = "capabilities"

    key = Column(String(100), primary_key=True)
    description = Column(Text, nullable=False)


class RoleTemplateCapabilityModel(Base):
    __tablename__ = "role_template_capabilities"

    role_template_id = Column(String(36), ForeignKey("role_templates.id"), primary_key=True)
    capability_key = Column(String(100), ForeignKey("capabilities.key"), primary_key=True)


class ProjectMembershipModel(Base):
    """A user's role on one specific project. Not consulted for an org owner (see
    MembershipModel); every other user needs an explicit row to act on a project."""
    __tablename__ = "project_memberships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    role_template_id = Column(String(36), ForeignKey("role_templates.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("uq_project_memberships_user_project", "user_id", "project_id", unique=True),)


# -- Guided Workspace journey engine (GW1; docs/product/JOURNEY_MANIFEST.md) -------
#
# One row per (project, subpoint): status is tracked at the subpoint level, and a
# group's/section's status is DERIVED from its subpoints at read time (packages/domain/
# journey.py), never stored redundantly. jrn_id values and their shape (JRN-<section>,
# JRN-<section>.<group>, JRN-<section>.<group>.<subpoint>) come from
# packages/domain/journey_manifest.yaml, which is the source of truth for which ids
# exist; this schema does not duplicate that structure or enforce it with a foreign key,
# since the manifest is a versioned file, not a database table (a manifest change is a
# code deploy, not a migration).


class JourneyItemStateModel(Base):
    """A subpoint's status for one project (JOURNEY_MANIFEST.md §6)."""
    __tablename__ = "journey_item_states"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    jrn_id = Column(String(50), nullable=False)  # subpoint id, e.g. "JRN-02.1.1"
    status = Column(String(50), default="not_started", nullable=False)
    not_applicable_reason = Column(Text, nullable=True)
    evidence_refs = Column(JSON, default=list, nullable=False)
    notes = Column(Text, nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (Index("uq_journey_item_states_project_jrn", "project_id", "jrn_id", unique=True),)


class JourneySectionEventModel(Base):
    """An explicit 'Continue to Next Section' transition (JOURNEY_MANIFEST.md §6, step
    8). Append-only: a section can be re-entered and re-completed, but history is never
    overwritten (step 9) -- each continue adds a new row."""
    __tablename__ = "journey_section_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    section_id = Column(String(20), nullable=False)  # e.g. "JRN-02"
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    group_statuses_snapshot = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class JourneyStalenessModel(Base):
    """An item marked stale by an upstream change (JOURNEY_MANIFEST.md §6, step 10).
    Open (unresolved) rows are what makes journey_item_states.status report "stale" for
    an otherwise-completed item; resolving one is a re-review action, not a deletion."""
    __tablename__ = "journey_staleness"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    jrn_id = Column(String(50), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    caused_by = Column(String(100), nullable=False)  # e.g. "screenplay_version_approved"
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)


class IdempotencyKeyModel(Base):
    """A client-supplied Idempotency-Key and the response it produced (TFD-OPS-004).

    Scoped to the authenticated user: the same key from two users is two records. A
    record is ``in_progress`` while the first request runs and ``completed`` once its
    response (any status below 500) is stored for replay.
    """

    __tablename__ = "idempotency_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    key = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    request_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False)  # in_progress, completed
    response_status = Column(Integer, nullable=True)
    response_body = Column(LargeBinary, nullable=True)
    response_content_type = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("uq_idempotency_keys_org_user_key", "organization_id", "user_id", "key", unique=True),)
