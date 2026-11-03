"""Canonical status vocabularies.

Values are persisted as plain strings, so changing a value requires a data migration.
"""

from enum import Enum


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
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    DECIDED = "decided"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class CandidateStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class OutboxStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditAction(str, Enum):
    PROJECT_CREATED = "project_created"
    ASSET_UPLOADED = "asset_uploaded"
    WORKFLOW_STARTED = "workflow_started"
    CANDIDATES_EXTRACTED = "candidates_extracted"
    APPROVAL_DECIDED = "approval_decided"
    SCRIPT_INTELLIGENCE_COMMITTED = "script_intelligence_committed"
    SCRIPT_INTELLIGENCE_REJECTED = "script_intelligence_rejected"


SCRIPT_INTELLIGENCE_GRAPH_ID = "script_intelligence"
SCRIPT_INTELLIGENCE_GRAPH_VERSION = "1.0"
SCRIPT_INTELLIGENCE_APPROVAL_SCOPE = "script_intelligence_candidates"
