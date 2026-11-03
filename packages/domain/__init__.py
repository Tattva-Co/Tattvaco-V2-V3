"""Domain vocabulary, errors and invariants. No I/O lives here."""

from packages.domain.enums import (
    ApprovalDecision,
    ApprovalStatus,
    AssetType,
    AuditAction,
    CandidateStatus,
    OutboxStatus,
    ProjectStatus,
    WorkflowStatus,
)
from packages.domain.errors import (
    DomainInvariantError,
    InvalidStateError,
    NotFoundError,
    PayloadTooLargeError,
    TenantAccessViolation,
    UnsupportedMediaTypeError,
    ValidationFailure,
    VersionConflictError,
)
from packages.domain.invariants import assert_expected_version, assert_project_scope

__all__ = [
    "ApprovalDecision",
    "ApprovalStatus",
    "AssetType",
    "AuditAction",
    "CandidateStatus",
    "OutboxStatus",
    "ProjectStatus",
    "WorkflowStatus",
    "DomainInvariantError",
    "InvalidStateError",
    "NotFoundError",
    "PayloadTooLargeError",
    "TenantAccessViolation",
    "UnsupportedMediaTypeError",
    "ValidationFailure",
    "VersionConflictError",
    "assert_expected_version",
    "assert_project_scope",
]
