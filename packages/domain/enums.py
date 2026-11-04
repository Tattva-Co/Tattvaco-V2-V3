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
    RESEARCH_QUESTION_CREATED = "research_question_created"
    RESEARCH_SOURCE_RECORDED = "research_source_recorded"
    RESEARCH_COMMITTED = "research_committed"
    RESEARCH_REJECTED = "research_rejected"
    STORYBOARD_COMMITTED = "storyboard_committed"
    STORYBOARD_REJECTED = "storyboard_rejected"


class ShotType(str, Enum):
    ESTABLISHING = "establishing"
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_THE_SHOULDER = "over_the_shoulder"
    POV = "pov"


class SourceTier(str, Enum):
    TIER_0 = "tier_0_project"
    TIER_1 = "tier_1_primary"
    TIER_2 = "tier_2_scholarly"
    TIER_3 = "tier_3_discovery"


class ClaimClass(str, Enum):
    FACT = "historical_fact"
    INTERPRETATION = "historical_interpretation"
    CONTESTED = "contested_claim"
    CREATIVE_DRAMATIZATION = "creative_dramatization"
    USER_ASSERTION = "user_assertion"
    UNVERIFIED = "unverified"


class QuestionStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


class ConflictStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


SCRIPT_INTELLIGENCE_GRAPH_ID = "script_intelligence"
SCRIPT_INTELLIGENCE_GRAPH_VERSION = "1.0"
SCRIPT_INTELLIGENCE_APPROVAL_SCOPE = "script_intelligence_candidates"

HISTORICAL_RESEARCH_GRAPH_ID = "historical_research"
HISTORICAL_RESEARCH_GRAPH_VERSION = "1.0"
HISTORICAL_RESEARCH_APPROVAL_SCOPE = "historical_research_candidates"

STORYBOARD_INTELLIGENCE_GRAPH_ID = "storyboard_intelligence"
STORYBOARD_INTELLIGENCE_GRAPH_VERSION = "1.0"
STORYBOARD_INTELLIGENCE_APPROVAL_SCOPE = "storyboard_candidates"
