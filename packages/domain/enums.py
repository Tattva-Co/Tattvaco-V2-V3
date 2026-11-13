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


class ScreenplayVersionStatus(str, Enum):
    """D2 (TFD-SCR-002/003, PRD §3.1 state diagram):
    draft -> in_review -> approved_locked -> superseded
                 |---------> rejected
                 <---------  (management requests changes, back to draft)
    """

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED_LOCKED = "approved_locked"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SuggestionKind(str, Enum):
    """D2 (TFD-SCR-005): the 7 kinds of AI creative suggestion (PRD §3 Workflow 2 /
    SCREEN_INVENTORY_AND_BEHAVIOUR.md S-SCR-04)."""

    ALTERNATIVE_SCENE = "alternative_scene"
    DIALOGUE_IMPROVEMENT = "dialogue_improvement"
    TRANSITION = "transition"
    STORYTELLING_OPPORTUNITY = "storytelling_opportunity"
    DRAMATIC_IMPROVEMENT = "dramatic_improvement"
    CHARACTER_DEVELOPMENT = "character_development"
    PACING = "pacing"


class SuggestionDisposition(str, Enum):
    PENDING = "pending"
    ACCEPTED_FOR_REVISION = "accepted_for_revision"
    REJECTED = "rejected"
    DEFERRED = "deferred"


#: D2 (TFD-SCR-010, PRD §3.1 invariant 4): a canonical item an impact analysis flagged
#: for human review after the screenplay version producing it was superseded. Nothing
#: else changes about the row -- no content, no status transition of its own -- "nothing
#: propagates automatically".
REVIEW_STATUS_REQUIRED = "review_required"


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
    # D2 (TFD-SCR-007/AT-SCR-007.3): management review of a screenplay revision has a
    # third, non-terminal outcome -- the revision returns to `draft` for more editing,
    # rather than being approved or permanently rejected. The 4 pre-existing LangGraph
    # review flows (script/research/storyboard/film-bible) never construct this value,
    # so their own APPROVED/else-REJECTED routing is unaffected by adding it here.
    CHANGES_REQUESTED = "changes_requested"


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
    SCREENPLAY_VERSION_IMPORTED = "screenplay_version_imported"
    SCREENPLAY_REVISION_CREATED = "screenplay_revision_created"
    SCREENPLAY_REVISION_EDITED = "screenplay_revision_edited"
    SCREENPLAY_REVISION_SUBMITTED = "screenplay_revision_submitted"
    SCREENPLAY_REVISION_APPROVED = "screenplay_revision_approved"
    SCREENPLAY_REVISION_REJECTED = "screenplay_revision_rejected"
    SCREENPLAY_REVISION_CHANGES_REQUESTED = "screenplay_revision_changes_requested"
    SCREENPLAY_LOCKED_MUTATION_BLOCKED = "screenplay_locked_mutation_blocked"
    SCREENPLAY_LEGACY_LOCK_CONFIRMED = "screenplay_legacy_lock_confirmed"
    SCREENPLAY_SUGGESTIONS_GENERATED = "screenplay_suggestions_generated"
    SCREENPLAY_SUGGESTION_DECIDED = "screenplay_suggestion_decided"
    IMPACT_ANALYSIS_CREATED = "impact_analysis_created"
    CHARACTER_VERSION_DRAFTED = "character_version_drafted"
    CHARACTER_VERSION_APPROVED = "character_version_approved"
    CHARACTER_VERSION_REJECTED = "character_version_rejected"
    CHARACTER_FACIAL_REFERENCE_ADDED = "character_facial_reference_added"
    CHARACTER_STATE_CREATED = "character_state_created"
    MEASUREMENT_RECORDED = "measurement_recorded"
    MEASUREMENT_CORRECTED = "measurement_corrected"
    MEASUREMENT_VERIFIED = "measurement_verified"
    PERFORMER_CREATED = "performer_created"
    CONSENT_DRAFTED = "consent_drafted"
    CONSENT_APPROVED = "consent_approved"
    CONSENT_REJECTED = "consent_rejected"
    CONSENT_REVOKED = "consent_revoked"
    VOICE_PROFILE_CREATED = "voice_profile_created"
    CONSENT_GATE_BLOCKED = "consent_gate_blocked"


class CharacterVersionStatus(str, Enum):
    """D4 (TFD-CHR-006): editing a field creates a draft; approval promotes it to the
    character's new current version, leaving every earlier version exactly as it was."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProvenanceStatus(str, Enum):
    """D4 (TFD-CHR-005): the status half of a characteristic's provenance envelope.
    'estimated' must never render as verified (AT-CHR-005.2)."""

    ESTIMATED = "estimated"
    VERIFIED = "verified"
    APPROVED = "approved"
    DISPUTED = "disputed"


class MeasurementStatus(str, Enum):
    """D4 (TFD-PHY-002/004): a body_measurements row's lifecycle. 'measured' is a direct
    human observation (tape, fitting); 'estimated' always starts from an AI/photograph
    source and can never become 'verified' without an independent measured/scan
    observation superseding it (AT-PHY-004.1)."""

    ESTIMATED = "estimated"
    MEASURED = "measured"
    VERIFIED = "verified"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"


class CaptureMethod(str, Enum):
    """D4 (TFD-PHY-002/004). Values match ACCEPTANCE_CRITERIA.md's literal AT-PHY-004
    text (`ai_estimate`, `calibrated_scan`) rather than the longer architecture-draft
    vocabulary, since the acceptance criteria are the authoritative source for FD-V1."""

    MANUAL_ENTRY = "manual_entry"
    AI_ESTIMATE = "ai_estimate"
    CALIBRATED_SCAN = "calibrated_scan"
    MANUAL_CORRECTION = "manual_correction"
    COSTUME_DEPARTMENT_RECORD = "costume_department_record"
    PERFORMER_SELF_REPORTED = "performer_self_reported"


class ConsentStatus(str, Enum):
    """D4 (TFD-CNS-002/004): a performer_consents row's lifecycle."""

    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


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
