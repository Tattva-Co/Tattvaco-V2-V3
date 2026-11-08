"""RBAC on the journey engine (GW1 + C5): a group's act_capability/approval_capability
genuinely gates journey actions, and the read view honestly reports what the caller can
and cannot do (can_act/can_approve) rather than only enforcing it on write."""

from __future__ import annotations

import uuid

from packages.persistence.database import SessionLocal
from packages.persistence.models import MembershipModel, ProjectMembershipModel, UserModel
from packages.persistence.repositories import RoleTemplateRepository
from tests.support import as_actor, create_project


def _add_plain_member(org_id: str) -> str:
    """A second user in the SAME organization, as a plain 'member' with no project of
    their own yet -- the realistic shape of "a second person signs into the shared org
    and creates their own project" (apps/api/routers/auth.py dev-login path)."""
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            UserModel(
                id=user_id, organization_id=org_id, email=f"{user_id[:8]}@member.example", full_name="New Member", role="creator"
            )
        )
        db.flush()
        db.add(MembershipModel(user_id=user_id, organization_id=org_id, org_role="member", status="active"))
        db.commit()
    finally:
        db.close()
    return user_id


def _add_viewer(org_id: str, project_id: str) -> str:
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(UserModel(id=user_id, organization_id=org_id, email=f"{user_id[:8]}@viewer.example", full_name="Viewer", role="creator"))
        db.flush()
        db.add(MembershipModel(user_id=user_id, organization_id=org_id, org_role="member", status="active"))
        viewer_template = RoleTemplateRepository(db).get_by_key(org_id, "viewer")
        db.add(ProjectMembershipModel(user_id=user_id, project_id=project_id, role_template_id=viewer_template.id))
        db.commit()
    finally:
        db.close()
    return user_id


def test_viewer_can_read_the_journey_but_cannot_act_on_a_group(client, tenant):
    project = create_project(client, tenant)
    viewer = _add_viewer(tenant.org_id, project["id"])

    journey = client.get(f"/api/v1/projects/{project['id']}/journey", headers=as_actor(viewer)).json()
    group = next(g for s in journey for g in s["groups"] if g["id"] == "JRN-05.3")  # act_capability: canon.propose
    assert group["can_act"] is False, "viewer's role template does not grant canon.propose"

    resp = client.post(
        f"/api/v1/projects/{project['id']}/journey/items/JRN-05.3.1", json={"action": "draft"}, headers=as_actor(viewer)
    )
    assert resp.status_code == 403, resp.text


def test_can_act_is_true_for_a_role_that_actually_holds_the_capability(client, tenant):
    project = create_project(client, tenant)
    journey = client.get(f"/api/v1/projects/{project['id']}/journey", headers=as_actor(tenant.user_id)).json()
    group = next(g for s in journey for g in s["groups"] if g["id"] == "JRN-05.3")
    assert group["can_act"] is True, "the project owner (org owner) can act on everything"


def test_approval_capability_is_enforced_separately_from_act_capability(client, tenant):
    """JRN-02.4 (Approved screenplay lock): act_capability canon.propose, but the
    validate subpoint's approval_capability is screenplay.approve_lock. A director-role
    user (who has canon.propose but not screenplay.approve_lock) can draft it, but
    cannot complete the approval step."""
    project = create_project(client, tenant)
    editor = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(UserModel(id=editor, organization_id=tenant.org_id, email=f"{editor[:8]}@director.example", full_name="Director", role="creator"))
        db.flush()
        db.add(MembershipModel(user_id=editor, organization_id=tenant.org_id, org_role="member", status="active"))
        director_template = RoleTemplateRepository(db).get_by_key(tenant.org_id, "director")
        db.add(ProjectMembershipModel(user_id=editor, project_id=project["id"], role_template_id=director_template.id))
        db.commit()
    finally:
        db.close()

    draft = client.post(
        f"/api/v1/projects/{project['id']}/journey/items/JRN-02.4.2", json={"action": "draft"}, headers=as_actor(editor)
    )
    assert draft.status_code == 200, draft.text

    complete = client.post(
        f"/api/v1/projects/{project['id']}/journey/items/JRN-02.4.2", json={"action": "complete"}, headers=as_actor(editor)
    )
    assert complete.status_code == 403, complete.text


def test_a_plain_member_project_creator_can_complete_the_first_required_journey_section(client, tenant):
    """Regression test for a real gap found building GW2: a plain org 'member' (not the
    org owner) creates their own project via POST /projects. JRN-01 (section 1 of the
    Guided Workspace journey) is act_capability=project.admin on every one of its groups,
    and gates every later section -- so the creator must be able to act on it, with no
    second role grant from anyone else. Before the project_owner role template existed,
    ProjectService.create auto-granted 'director', which does not hold project.admin, so
    this would have 403'd (see docs/audit/10, migration a9fb5bf54591)."""
    creator = _add_plain_member(tenant.org_id)

    created = client.post(
        "/api/v1/projects",
        json={"title": "Solo creator's project", "logline": "x", "genre": "Drama"},
        headers=as_actor(creator),
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    journey = client.get(f"/api/v1/projects/{project_id}/journey", headers=as_actor(creator)).json()
    group = next(g for s in journey for g in s["groups"] if g["id"] == "JRN-01.1")
    assert group["can_act"] is True, "the project creator must be able to act on their own project's setup"

    subpoint_id = group["subpoints"][0]["id"]
    complete = client.post(
        f"/api/v1/projects/{project_id}/journey/items/{subpoint_id}", json={"action": "complete"}, headers=as_actor(creator)
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "completed"
