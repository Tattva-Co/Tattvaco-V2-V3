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


class ProductionMode(str, Enum):
    """Project/scene/(sequence/character/shot when those tables exist)-level mode
    (D1, TFD-PRJ-003/004; PRD §2.2 inheritance: ``effective_mode(x) = x.mode ?? parent.mode``).
    Mirrors packages.domain.journey_manifest.yaml's enums.production_modes -- validated
    here too so an out-of-range value 422s at the API boundary (AT-PRJ-003.1), not just
    silently falls through the journey engine's applicability resolver."""

    FULLY_AI = "fully_ai"
    HYBRID_LIVE_ACTION = "hybrid_live_action"
    MIXED = "mixed"


class QualityProfile(str, Enum):
    """Visual quality profile (D1, TFD-PRJ-001). PRD §8 names the field but not its
    values (DEC-028: per-format defaults are open); this is a provisional 3-tier
    placeholder pending production validation, not a specified product requirement."""

    DRAFT = "draft"
    STANDARD = "standard"
    PREMIUM = "premium"


class ProjectScale(str, Enum):
    """Project scale (D1, TFD-PRJ-001). Same provisional status as QualityProfile."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class AssetType(str, Enum):
    SCRIPT = "script"
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    PRODUCTION_PACKAGE = "production_package"


class AssetScanStatus(str, Enum):
    """Malware-scan lifecycle for an uploaded asset (C7). An asset is unusable by any
    workflow (packages/services/script_review.py::load_script_text) until CLEAN -- today
    that happens synchronously at upload time (packages/services/scanning.py's NoOpScanner
    always reports clean), but the state model is real so a future async scanner has
    somewhere to report INFECTED without a schema change."""

    QUARANTINED = "quarantined"
    CLEAN = "clean"
    INFECTED = "infected"


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
    FAILED = "failed"  # retained for schema history; a failed attempt now returns the
    # task to PENDING (if attempts remain) or DEAD_LETTERED (C6), never FAILED.
    DEAD_LETTERED = "dead_lettered"


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
    VISUAL_RULE_CREATED = "visual_rule_created"
    FILM_BIBLE_COMMITTED = "film_bible_committed"
    FILM_BIBLE_REJECTED = "film_bible_rejected"
    PROJECT_UPDATED = "project_updated"
    PROJECT_ARCHIVED = "project_archived"
    PROJECT_UNARCHIVED = "project_unarchived"
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_MEMBER_ROLE_CHANGED = "project_member_role_changed"
    PROJECT_MEMBER_REMOVED = "project_member_removed"
    OUTPUT_PROFILE_CREATED = "output_profile_created"
    OUTPUT_PROFILE_UPDATED = "output_profile_updated"
    OUTPUT_PROFILE_DELETED = "output_profile_deleted"
    EPISODE_CREATED = "episode_created"


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


class VisualRuleCategory(str, Enum):
    TONE_AESTHETIC = "tone_aesthetic"
    COLOR_PALETTE = "color_palette"
    LIGHTING_ATMOSPHERE = "lighting_atmosphere"
    ARCHITECTURAL_ENVIRONMENT = "architectural_environment"
    MATERIAL_CULTURE = "material_culture"
    CAMERA_LANGUAGE = "camera_language"


class RuleStrictness(str, Enum):
    MANDATORY = "mandatory"
    GUIDELINE = "guideline"
    DEVIATION = "deliberate_deviation"


FILM_BIBLE_GRAPH_ID = "film_bible_synthesis"
FILM_BIBLE_GRAPH_VERSION = "1.0"
FILM_BIBLE_APPROVAL_SCOPE = "film_bible_rules"
