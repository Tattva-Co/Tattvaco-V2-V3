"""SQLAlchemy ORM models representing canonical entities, workflow runs, and audit logs."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from packages.persistence.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


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
    size_bytes = Column(Integer, nullable=False)
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
