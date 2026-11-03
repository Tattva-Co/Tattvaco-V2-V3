"""Tests enforcing strict tenant and project isolation invariants."""

import pytest
from packages.domain.invariants import (
    assert_expected_version,
    assert_project_scope,
    TenantAccessViolation,
    VersionConflictError,
)


def test_project_scope_enforces_organization_match():
    # Matching org succeeds
    assert_project_scope(
        actor_org_id="org-tattva",
        project_org_id="org-tattva",
    )

    # Cross-tenant attempt must raise TenantAccessViolation
    with pytest.raises(TenantAccessViolation) as exc_info:
        assert_project_scope(
            actor_org_id="org-adversary",
            project_org_id="org-tattva",
        )
    assert "Cross-organization access forbidden" in str(exc_info.value)


def test_project_scope_rejects_missing_org():
    with pytest.raises(TenantAccessViolation) as exc_info:
        assert_project_scope(
            actor_org_id="",
            project_org_id="org-tattva",
        )
    assert "Missing organization context" in str(exc_info.value)


def test_version_conflict_detection():
    # Matching version succeeds
    assert_expected_version(current_version=2, expected_version=2)

    # Stale version raises VersionConflictError
    with pytest.raises(VersionConflictError) as exc_info:
        assert_expected_version(current_version=3, expected_version=2)
    assert "version conflict" in str(exc_info.value).lower()
