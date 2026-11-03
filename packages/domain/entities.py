"""Canonical domain entities for Tattva AI Film Director.

Domain entities are the authoritative business objects of the system.
AI graphs and external systems propose candidates; only validated domain operations
commit canonical entities to the project database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AssetType(str, Enum):
    SCRIPT = "script"
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    PRODUCTION_PACKAGE = "production_package"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED_FOR_REVIEW = "paused_for_review"
    RESUMING = "resuming"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    DECIDED = "decided"
    EXPIRED = "expired"


class CandidateStatus(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Organization:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class User:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str = ""
    email: str = ""
    full_name: str = ""
    role: str = "creator"  # admin, creator, reviewer, viewer
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str = ""
    title: str = ""
    logline: Optional[str] = None
    genre: Optional[str] = None
    status: ProjectStatus = ProjectStatus.DRAFT
    current_version: int = 1
    created_by: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class ProjectVersion:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    version_number: int = 1
    branch_name: str = "main"
    commit_message: str = ""
    committed_by: str = ""
    snapshot_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class Asset:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    organization_id: str = ""
    filename: str = ""
    mime_type: str = ""
    size_bytes: int = 0
    checksum_sha256: str = ""
    storage_path: str = ""
    asset_type: AssetType = AssetType.SCRIPT
    is_original: bool = True
    parent_asset_id: Optional[str] = None
    uploaded_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class WorkflowRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_id: str = "G-01"
    graph_version: str = "1.0"
    project_id: str = ""
    organization_id: str = ""
    actor_id: str = ""
    expected_project_version: int = 1
    status: WorkflowStatus = WorkflowStatus.PENDING
    input_asset_ids: List[str] = field(default_factory=list)
    output_refs: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class ApprovalRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_run_id: str = ""
    project_id: str = ""
    organization_id: str = ""
    scope: str = "script_intelligence_candidates"
    candidate_summary: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision: Optional[ApprovalDecision] = None
    decision_notes: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class AuditEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    organization_id: str = ""
    actor_id: str = ""
    action: str = ""
    target_type: str = ""
    target_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


# Domain entities specific to Script Intelligence
@dataclass
class SceneCandidate:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    scene_number: int = 1
    heading: str = ""  # e.g. "EXT. RAJPUT FORT - DAWN"
    setting: str = "EXT"  # INT / EXT
    location_name: str = ""
    time_of_day: str = "DAY"  # DAY, NIGHT, DAWN, DUSK
    summary: str = ""
    source_locator: str = ""  # e.g. "lines 1-45"
    characters_present: List[str] = field(default_factory=list)
    status: CandidateStatus = CandidateStatus.PROPOSED


@dataclass
class EntityCandidate:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    name: str = ""
    category: str = "character"  # character, location, prop, costume
    description: str = ""
    source_locator: str = ""
    confidence: float = 0.9
    status: CandidateStatus = CandidateStatus.PROPOSED
