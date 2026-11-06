"""Negative authorization matrix for RBAC (ADR-003 §2; docs/audit/08 SEC-03).

Before this milestone, any authenticated member of an organization could do anything to
any project in that organization: there was no concept of a role, only tenant isolation
(you couldn't touch another org's data, but anyone in your own org could touch all of
it). These tests prove the replacement actually restricts access rather than just adding
inert tables: a project_membership (or its absence) and a role template's capability
bundle genuinely gate what a request can do.
"""

from __future__ import annotations

import io
import uuid

from packages.persistence.database import SessionLocal
from packages.persistence.models import MembershipModel, ProjectMembershipModel, UserModel
from packages.persistence.repositories import RoleTemplateRepository
from tests.support import SAMPLE_SCREENPLAY, as_actor, create_project


def _upload_as(client, actor_user_id: str, project_id: str):
    return client.post(
        f"/api/v1/projects/{project_id}/assets/upload",
        files={"file": ("chronicle.fountain", io.BytesIO(SAMPLE_SCREENPLAY.encode()), "text/plain")},
        headers=as_actor(actor_user_id),
    )


def _add_org_member(org_id: str, *, org_role: str = "member", status: str = "active") -> str:
    """A second user in the SAME organization as the owning tenant, with no project
    access of their own unless a test grants it via _grant_project_role."""
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            UserModel(
                id=user_id,
                organization_id=org_id,
                email=f"{user_id[:8]}@member.example",
                full_name="Org Member",
                role="creator",
            )
        )
        db.flush()
        db.add(MembershipModel(user_id=user_id, organization_id=org_id, org_role=org_role, status=status))
        db.commit()
    finally:
        db.close()
    return user_id


def _grant_project_role(org_id: str, user_id: str, project_id: str, role_key: str) -> None:
    db = SessionLocal()
    try:
        template = RoleTemplateRepository(db).get_by_key(org_id, role_key)
        assert template is not None, f"no seeded role template {role_key!r} for org {org_id}"
        db.add(ProjectMembershipModel(user_id=user_id, project_id=project_id, role_template_id=template.id))
        db.commit()
    finally:
        db.close()


def test_member_with_no_project_membership_cannot_read_an_existing_project(client, tenant):
    project = create_project(client, tenant, title="Owner's project")
    outsider_member = _add_org_member(tenant.org_id)

    resp = client.get(f"/api/v1/projects/{project['id']}", headers=as_actor(outsider_member))
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"] == "TenantAccessViolation"


def test_member_with_no_project_membership_can_still_create_their_own_project(client, tenant):
    """project.create is an org-level capability; it doesn't require a pre-existing
    project_membership, and the creator is auto-granted 'director' on what they create."""
    outsider_member = _add_org_member(tenant.org_id)

    resp = client.post(
        "/api/v1/projects",
        json={"title": "My own project", "logline": "x", "genre": "Drama"},
        headers=as_actor(outsider_member),
    )
    assert resp.status_code == 201, resp.text
    new_project_id = resp.json()["id"]

    # And, having created it, they can now read it.
    read = client.get(f"/api/v1/projects/{new_project_id}", headers=as_actor(outsider_member))
    assert read.status_code == 200, read.text


def test_suspended_membership_is_denied_even_with_a_project_role(client, tenant):
    project = create_project(client, tenant, title="Suspension check")
    suspended_user = _add_org_member(tenant.org_id, status="suspended")
    _grant_project_role(tenant.org_id, suspended_user, project["id"], "management")

    resp = client.get(f"/api/v1/projects/{project['id']}", headers=as_actor(suspended_user))
    assert resp.status_code == 403, resp.text


def test_viewer_can_read_but_not_upload_or_trigger_workflows(client, tenant):
    project = create_project(client, tenant, title="Viewer scope")
    viewer = _add_org_member(tenant.org_id)
    _grant_project_role(tenant.org_id, viewer, project["id"], "viewer")

    read = client.get(f"/api/v1/projects/{project['id']}", headers=as_actor(viewer))
    assert read.status_code == 200, read.text

    upload = _upload_as(client, viewer, project["id"])
    assert upload.status_code == 403, upload.text
    assert upload.json()["error"] == "TenantAccessViolation"

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/historical-research",
        json={"topic": "Anything", "sync_execution": True},
        headers=as_actor(viewer),
    )
    assert trigger.status_code == 403, trigger.text

    propose = client.post(
        f"/api/v1/projects/{project['id']}/research/questions",
        json={"text": "A question?"},
        headers=as_actor(viewer),
    )
    assert propose.status_code == 403, propose.text


def test_crew_editor_can_upload_and_run_workflows_but_not_approve(client, tenant):
    project = create_project(client, tenant, title="Crew scope")
    editor = _add_org_member(tenant.org_id)
    _grant_project_role(tenant.org_id, editor, project["id"], "crew_editor")

    upload = _upload_as(client, editor, project["id"])
    assert upload.status_code == 200, upload.text

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/historical-research",
        json={"topic": "Fortification design", "sync_execution": True},
        headers=as_actor(editor),
    )
    assert trigger.status_code == 200, trigger.text
    approval_id = trigger.json()["approval_request_id"]

    decide = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "approved"},
        headers=as_actor(editor),
    )
    assert decide.status_code == 403, decide.text
    assert decide.json()["error"] == "TenantAccessViolation"


def test_management_alone_can_be_distinguished_from_director_by_capability(tenant):
    """Both roles can approve.creative; cost.approve is management-only. This test locks
    in that the two bundles are genuinely different, not copies of each other."""
    director_db = SessionLocal()
    try:
        director_caps = RoleTemplateRepository(director_db).capabilities_for(
            RoleTemplateRepository(director_db).get_by_key(tenant.org_id, "director").id
        )
        management_caps = RoleTemplateRepository(director_db).capabilities_for(
            RoleTemplateRepository(director_db).get_by_key(tenant.org_id, "management").id
        )
    finally:
        director_db.close()
    assert "cost.approve" in management_caps
    assert "cost.approve" not in director_caps
    assert "approval.creative" in director_caps
    assert "approval.creative" in management_caps


def test_org_owner_can_act_on_a_project_with_no_explicit_project_membership(client, tenant):
    """The creator already gets an explicit project_membership (ProjectService.create),
    so this proves the owner BYPASS specifically: a second owner-level user, added to the
    org after the project already exists, with no project_membership row at all."""
    project = create_project(client, tenant, title="Owner bypass")
    second_owner = _add_org_member(tenant.org_id, org_role="owner")

    resp = client.get(f"/api/v1/projects/{project['id']}", headers=as_actor(second_owner))
    assert resp.status_code == 200, resp.text

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/historical-research",
        json={"topic": "Owner bypass check", "sync_execution": True},
        headers=as_actor(second_owner),
    )
    assert trigger.status_code == 200, trigger.text


def test_a_users_membership_in_one_org_grants_nothing_in_another(client, tenant, other_tenant):
    """Sanity check that RBAC is layered on top of, not instead of, tenant isolation."""
    project = create_project(client, tenant, title="Cross-org check")
    resp = client.get(f"/api/v1/projects/{project['id']}", headers=as_actor(other_tenant.user_id))
    assert resp.status_code == 404, resp.text  # tenant isolation: no existence oracle
