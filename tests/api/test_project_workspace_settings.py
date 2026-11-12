"""D1 (Project Workspace & Setup): formats/templates, output profiles, episodes,
production-mode inheritance, project update/archive, members & roles, and the
Project Overview summary. Acceptance criteria cited are
docs/product/ACCEPTANCE_CRITERIA.md §3.1/3.2.
"""

from __future__ import annotations

import uuid

from packages.persistence.database import SessionLocal
from packages.persistence.models import MembershipModel, SceneModel, UserModel
from tests.support import as_actor, create_project


def _add_org_member(org_id: str, *, email: str | None = None) -> tuple[str, str]:
    user_id = str(uuid.uuid4())
    email = email or f"{user_id[:8]}@member.example"
    db = SessionLocal()
    try:
        db.add(UserModel(id=user_id, organization_id=org_id, email=email, full_name="New Member", role="creator"))
        db.flush()
        db.add(MembershipModel(user_id=user_id, organization_id=org_id, org_role="member", status="active"))
        db.commit()
    finally:
        db.close()
    return user_id, email


def _add_scene(project_id: str, org_id: str, *, scene_number: int, production_mode: str | None = None) -> str:
    db = SessionLocal()
    try:
        scene = SceneModel(
            project_id=project_id,
            organization_id=org_id,
            scene_number=scene_number,
            heading=f"INT. ROOM {scene_number}",
            setting="INT",
            location_name="Room",
            time_of_day="DAY",
            summary="Summary.",
            source_locator=f"Scene {scene_number}",
            characters_present=[],
            project_version=1,
            production_mode=production_mode,
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)
        return scene.id
    finally:
        db.close()


# -- TFD-PRJ-001: creation ----------------------------------------------------


def test_a_project_can_be_created_with_only_title_and_mode(client, tenant):
    resp = client.post(
        "/api/v1/projects", json={"title": "River", "production_mode": "mixed"}, headers=as_actor(tenant.user_id)
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["current_version"] == 1
    assert body["production_mode"] == "mixed"
    assert body["format_template_key"] is None
    assert body["quality_profile"] is None
    assert body["scale"] is None

    audit = client.get(f"/api/v1/projects/{body['id']}/audit-log", headers=as_actor(tenant.user_id)).json()
    assert any(e["action"] == "project_created" for e in audit)


def test_the_legacy_title_logline_genre_body_still_works_and_defaults_to_mixed(client, tenant):
    resp = client.post(
        "/api/v1/projects",
        json={"title": "Legacy Project", "logline": "x", "genre": "Drama"},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["production_mode"] == "mixed"


def test_an_out_of_range_production_mode_is_rejected(client, tenant):
    resp = client.post(
        "/api/v1/projects", json={"title": "Bad Mode", "production_mode": "nonsense"}, headers=as_actor(tenant.user_id)
    )
    assert resp.status_code == 422, resp.text


def test_an_unknown_format_template_key_is_rejected(client, tenant):
    resp = client.post(
        "/api/v1/projects",
        json={"title": "Bad Template", "production_mode": "mixed", "format_template_key": "not_a_real_format"},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 422, resp.text


# -- TFD-PRJ-002: list/get/update/archive scoped to memberships ---------------


def test_list_projects_is_scoped_to_the_callers_own_memberships(client, tenant):
    create_project(client, tenant, title="Owner's project")
    outsider, _ = _add_org_member(tenant.org_id)

    own_project = client.post(
        "/api/v1/projects", json={"title": "Outsider's own project"}, headers=as_actor(outsider)
    ).json()

    listing = client.get("/api/v1/projects", headers=as_actor(outsider)).json()
    assert [p["id"] for p in listing] == [own_project["id"]]


def test_update_project_metadata_is_audited_with_before_and_after(client, tenant):
    project = create_project(client, tenant)
    resp = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"title": "New Title", "quality_profile": "premium"},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "New Title"
    assert resp.json()["quality_profile"] == "premium"

    audit = client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=as_actor(tenant.user_id)).json()
    update_event = next(e for e in audit if e["action"] == "project_updated")
    assert update_event["details"]["before"]["title"] != update_event["details"]["after"]["title"]


def test_archiving_hides_a_project_from_the_default_list_and_unarchiving_restores_it(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)

    archived = client.post(f"/api/v1/projects/{project['id']}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

    listing = client.get("/api/v1/projects", headers=headers).json()
    assert project["id"] not in [p["id"] for p in listing]

    listing_with_archived = client.get("/api/v1/projects?include_archived=true", headers=headers).json()
    assert project["id"] in [p["id"] for p in listing_with_archived]

    unarchived = client.post(f"/api/v1/projects/{project['id']}/unarchive", headers=headers)
    assert unarchived.status_code == 200, unarchived.text
    assert unarchived.json()["status"] == "active"

    listing_after = client.get("/api/v1/projects", headers=headers).json()
    assert project["id"] in [p["id"] for p in listing_after]

    audit = client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=headers).json()
    actions = [e["action"] for e in audit]
    assert "project_archived" in actions
    assert "project_unarchived" in actions


# -- TFD-PRJ-004: mode override and inheritance --------------------------------


def test_a_scene_level_mode_override_is_reflected_in_the_overview_mode_distribution(client, tenant):
    project = create_project(client, tenant, production_mode="fully_ai")
    _add_scene(project["id"], tenant.org_id, scene_number=1, production_mode=None)
    _add_scene(project["id"], tenant.org_id, scene_number=2, production_mode="hybrid_live_action")

    summary = client.get(f"/api/v1/projects/{project['id']}/summary", headers=as_actor(tenant.user_id)).json()
    assert summary["scene_count_by_effective_mode"] == {"fully_ai": 1, "hybrid_live_action": 1}


# -- TFD-FMT-001/004: template catalogue --------------------------------------


def test_the_template_catalogue_has_exactly_13_formats(client, tenant):
    resp = client.get("/api/v1/project-templates", headers=as_actor(tenant.user_id))
    assert resp.status_code == 200, resp.text
    templates = resp.json()
    assert len(templates) == 13
    for t in templates:
        assert t["structure_type"] in ("linear", "episodic")
        assert t["default_output_profile"]["resolution"]


def test_the_reel_template_marks_sequence_planning_optional(client, tenant):
    templates = client.get("/api/v1/project-templates", headers=as_actor(tenant.user_id)).json()
    reel = next(t for t in templates if t["key"] == "reel")
    assert "JRN-07" in reel["optional_workflow_steps"]
    assert "JRN-07" not in reel["required_workflow_steps"]


# -- TFD-FMT-002: output profiles ----------------------------------------------


def test_output_profile_crud_roundtrip(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)

    created = client.post(
        f"/api/v1/projects/{project['id']}/output-profiles",
        json={"name": "16:9 Master", "resolution": "3840x2160", "aspect_ratio": "16:9", "is_default": True},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    profile_id = created.json()["id"]

    listing = client.get(f"/api/v1/projects/{project['id']}/output-profiles", headers=headers).json()
    assert [p["id"] for p in listing] == [profile_id]

    updated = client.patch(
        f"/api/v1/projects/{project['id']}/output-profiles/{profile_id}",
        json={"delivery_format": "ProRes 4444"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["delivery_format"] == "ProRes 4444"

    deleted = client.delete(f"/api/v1/projects/{project['id']}/output-profiles/{profile_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    assert client.get(f"/api/v1/projects/{project['id']}/output-profiles", headers=headers).json() == []


# -- TFD-FMT-003: episodes ------------------------------------------------------


def test_episode_create_and_list(client, tenant):
    project = create_project(client, tenant, production_mode="mixed")
    headers = as_actor(tenant.user_id)

    created = client.post(
        f"/api/v1/projects/{project['id']}/episodes",
        json={"episode_number": 1, "title": "Pilot"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    listing = client.get(f"/api/v1/projects/{project['id']}/episodes", headers=headers).json()
    assert [e["episode_number"] for e in listing] == [1]
    assert listing[0]["title"] == "Pilot"


def test_duplicate_episode_number_is_rejected(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    client.post(f"/api/v1/projects/{project['id']}/episodes", json={"episode_number": 1}, headers=headers)
    dup = client.post(f"/api/v1/projects/{project['id']}/episodes", json={"episode_number": 1}, headers=headers)
    assert dup.status_code == 409, dup.text


# -- S-TEAM-02: members & roles -------------------------------------------------


def test_project_owner_can_add_change_and_remove_a_member(client, tenant):
    project = create_project(client, tenant)
    owner_headers = as_actor(tenant.user_id)
    _, member_email = _add_org_member(tenant.org_id)

    added = client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"email": member_email, "role_template_key": "viewer"},
        headers=owner_headers,
    )
    assert added.status_code == 201, added.text
    assert added.json()["role_template_key"] == "viewer"
    member_user_id = added.json()["user_id"]

    listing = client.get(f"/api/v1/projects/{project['id']}/members", headers=owner_headers).json()
    assert {m["user_id"] for m in listing} == {tenant.user_id, member_user_id}

    changed = client.patch(
        f"/api/v1/projects/{project['id']}/members/{member_user_id}",
        json={"role_template_key": "director"},
        headers=owner_headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["role_template_key"] == "director"

    removed = client.delete(f"/api/v1/projects/{project['id']}/members/{member_user_id}", headers=owner_headers)
    assert removed.status_code == 204, removed.text
    listing_after = client.get(f"/api/v1/projects/{project['id']}/members", headers=owner_headers).json()
    assert member_user_id not in [m["user_id"] for m in listing_after]


def test_adding_a_member_who_is_not_an_org_member_is_rejected(client, tenant):
    project = create_project(client, tenant)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"email": "stranger@nowhere.example", "role_template_key": "viewer"},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 422, resp.text


def test_a_member_without_manage_members_cannot_add_another_member(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    director_id, director_email = _add_org_member(tenant.org_id)
    client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"email": director_email, "role_template_key": "director"},
        headers=headers,
    )
    _, third_email = _add_org_member(tenant.org_id)

    resp = client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"email": third_email, "role_template_key": "viewer"},
        headers=as_actor(director_id),
    )
    assert resp.status_code == 403, resp.text


def test_removing_the_projects_only_approve_lock_holder_is_blocked(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    # project_owner (auto-granted to the creator) holds screenplay.approve_lock, and is
    # the only member -- removing them would leave the project with no holder at all.
    resp = client.delete(f"/api/v1/projects/{project['id']}/members/{tenant.user_id}", headers=headers)
    assert resp.status_code == 409, resp.text


# -- TFD-PRJ-007: Project Overview summary -------------------------------------


def test_project_summary_reports_no_fabricated_data_for_features_that_do_not_exist_yet(client, tenant):
    project = create_project(client, tenant)
    summary = client.get(f"/api/v1/projects/{project['id']}/summary", headers=as_actor(tenant.user_id)).json()

    assert summary["canonical_screenplay_version"] is None
    assert summary["screenplay_lock_state"] == "none_locked"
    assert summary["unresolved_high_severity_findings_count"] == 0
    assert summary["project_version"] == 1
    assert summary["pending_approvals_count"] == 0
    assert summary["next_action"]["jrn_id"].startswith("JRN-01")
