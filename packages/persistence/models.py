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
    String,
    Text,
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
    current_version = Column(Integer, default=1, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ProjectVersionModel(Base):
    __tablename__ = "project_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    branch_name = Column(String(100), default="main", nullable=False)
    commit_message = Column(Text, nullable=False)
    committed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    snapshot_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


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
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class OutboxTaskModel(Base):
    """PostgreSQL-backed durable outbox for worker dispatching."""
    __tablename__ = "outbox_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, unique=True, index=True)
    task_type = Column(String(100), nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, claimed, completed, failed
    attempts = Column(Integer, default=0, nullable=False)
    claimed_by = Column(String(100), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ApprovalRequestModel(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
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


class SceneCandidateModel(Base):
    """Extracted scene candidates pending human approval."""
    __tablename__ = "scene_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    scene_number = Column(Integer, nullable=False)
    heading = Column(String(255), nullable=False)
    setting = Column(String(10), default="EXT", nullable=False)
    location_name = Column(String(255), nullable=False)
    time_of_day = Column(String(50), default="DAY", nullable=False)
    summary = Column(Text, nullable=False)
    source_locator = Column(String(100), nullable=False)
    characters_present = Column(JSON, default=list, nullable=False)
    status = Column(String(50), default="proposed", nullable=False)  # proposed, approved, rejected
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class EntityCandidateModel(Base):
    """Extracted entity candidates (characters, props, locations) pending human approval."""
    __tablename__ = "entity_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), default="character", nullable=False)
    description = Column(Text, nullable=True)
    source_locator = Column(String(100), nullable=False)
    confidence = Column(Float, default=0.9, nullable=False)
    status = Column(String(50), default="proposed", nullable=False)  # proposed, approved, rejected
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SceneModel(Base):
    """Canonical approved scenes in the project."""
    __tablename__ = "scenes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    scene_number = Column(Integer, nullable=False)
    heading = Column(String(255), nullable=False)
    setting = Column(String(10), nullable=False)
    location_name = Column(String(255), nullable=False)
    time_of_day = Column(String(50), nullable=False)
    summary = Column(Text, nullable=False)
    source_locator = Column(String(100), nullable=False)
    characters_present = Column(JSON, default=list, nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class EntityModel(Base):
    """Canonical approved entities (characters, locations, props)."""
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    source_locator = Column(String(100), nullable=False)
    project_version = Column(Integer, default=1, nullable=False)
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
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
