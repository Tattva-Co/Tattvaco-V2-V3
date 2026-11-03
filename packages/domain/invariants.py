"""Domain invariants and business policy assertions."""

from __future__ import annotations

from typing import Optional
from packages.domain.entities import Project, WorkflowRun, ApprovalRequest, ApprovalStatus


class DomainInvariantError(Exception):
    """Raised when a core domain invariant is violated."""
    pass


class TenantAccessViolation(DomainInvariantError):
    """Raised when cross-tenant or cross-project access is attempted."""
    pass


class VersionConflictError(DomainInvariantError):
    """Raised when an operation encounters an unexpected project version."""
    pass


def assert_project_scope(
    actor_org_id: str,
    project_org_id: str,
    actor_id: Optional[str] = None,
) -> None:
    """Enforce strict organization-level project scoping."""
    if not actor_org_id or not project_org_id:
        raise TenantAccessViolation("Missing organization context for project access.")
    if actor_org_id != project_org_id:
        raise TenantAccessViolation(
            f"Cross-organization access forbidden: actor org '{actor_org_id}' "
            f"does not match project org '{project_org_id}'."
        )


def assert_expected_version(current_version: int, expected_version: int) -> None:
    """Ensure optimistic locking on project mutations."""
    if current_version != expected_version:
        raise VersionConflictError(
            f"Stale project version conflict: expected version {expected_version}, "
            f"but current project version is {current_version}."
        )


def assert_can_resume(
    approval: ApprovalRequest,
    run: WorkflowRun,
    actor_id: str,
    actor_org_id: str,
) -> None:
    """Ensure an interrupted workflow run meets all preconditions to resume."""
    if approval.workflow_run_id != run.id:
        raise DomainInvariantError("Approval request does not match workflow run ID.")
    if approval.organization_id != actor_org_id:
        raise TenantAccessViolation("Reviewer does not belong to the approval organization.")
    if approval.status != ApprovalStatus.DECIDED:
        raise DomainInvariantError(f"Cannot resume run: approval status is {approval.status.value}, expected decided.")
