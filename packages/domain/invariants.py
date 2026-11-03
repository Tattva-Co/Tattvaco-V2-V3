"""Domain invariants and business policy assertions."""

from __future__ import annotations

from typing import Optional

from packages.domain.errors import (
    DomainInvariantError,
    TenantAccessViolation,
    VersionConflictError,
)

__all__ = [
    "DomainInvariantError",
    "TenantAccessViolation",
    "VersionConflictError",
    "assert_project_scope",
    "assert_expected_version",
]


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
