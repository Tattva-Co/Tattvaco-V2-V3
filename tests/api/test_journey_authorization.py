"""RBAC on the journey engine (GW1 + C5): a group's act_capability/approval_capability
genuinely gates journey actions, and the read view honestly reports what the caller can
and cannot do (can_act/can_approve) rather than only enforcing it on write."""

from __future__ import annotations

import uuid

from packages.persistence.database import SessionLocal
from packages.persistence.models import MembershipModel, ProjectMembershipModel, UserModel
from packages.persistence.repositories import RoleTemplateRepository
from tests.support import as_actor, create_project


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
