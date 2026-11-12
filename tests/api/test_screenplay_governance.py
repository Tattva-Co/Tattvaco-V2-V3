"""D2 (Screenplay & Governance): import, revisions, suggestions, management lock, and
impact analysis. Acceptance criteria cited are
docs/product/ACCEPTANCE_CRITERIA.md §3.5 (SCR).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    MembershipModel,
    ProjectMembershipModel,
    ProjectModel,
    ScreenplayVersionModel,
    UserModel,
)
from packages.persistence.repositories import RoleTemplateRepository
from tests.support import as_actor, create_project, import_screenplay_version, upload_script


def _add_member_with_role(org_id: str, project_id: str, role_key: str) -> str:
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            UserModel(
                id=user_id, organization_id=org_id, email=f"{user_id[:8]}@member.example", full_name="Crew Member", role="creator"
            )
        )
        db.flush()
        db.add(MembershipModel(user_id=user_id, organization_id=org_id, org_role="member", status="active"))
        template = RoleTemplateRepository(db).get_by_key(org_id, role_key)
        db.add(ProjectMembershipModel(user_id=user_id, project_id=project_id, role_template_id=template.id))
        db.commit()
    finally:
        db.close()
    return user_id


def _import_version(client, tenant, project_id):
    upload = upload_script(client, tenant, project_id)
    assert upload.status_code == 200, upload.text
    return import_screenplay_version(client, tenant, project_id, upload.json()["asset_id"])


# -- TFD-SCR-001: import ------------------------------------------------------


def test_importing_a_screenplay_creates_a_draft_v1_linked_to_its_asset(client, tenant):
    project = create_project(client, tenant)
    upload = upload_script(client, tenant, project["id"])
    version = import_screenplay_version(client, tenant, project["id"], upload.json()["asset_id"])

    assert version["status"] == "draft"
    assert version["version_number"] == 1
    assert version["source_asset_id"] == upload.json()["asset_id"]
    assert version["is_production_canonical"] is False


# -- TFD-SCR-002: lock and single canonical version ---------------------------


def test_management_approval_locks_a_version_as_the_sole_canonical(client, tenant):
    project = create_project(client, tenant)
    version = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)

    submitted = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}/submit",
        json={"justification": "Initial production lock."},
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "in_review"

    decided = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}/decide",
        json={"decision": "approved", "notes": "Locking for production."},
        headers=headers,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["version_status"] == "approved_locked"
    assert decided.json()["is_canonical"] is True

    reread = client.get(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}", headers=headers
    ).json()
    assert reread["locked_by"] == tenant.user_id
    assert reread["locked_at"] is not None


def test_a_non_management_actor_cannot_decide_a_revision(client, tenant):
    project = create_project(client, tenant)
    version = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}/submit",
        json={"justification": "Initial lock."},
        headers=headers,
    )
    director_id = _add_member_with_role(tenant.org_id, project["id"], "director")

    resp = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}/decide",
        json={"decision": "approved"},
        headers=as_actor(director_id),
    )
    assert resp.status_code == 403, resp.text


# -- TFD-SCR-003: locked versions are immutable --------------------------------


def test_editing_a_locked_version_is_rejected_with_screenplay_locked(client, tenant):
    project = create_project(client, tenant)
    version = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}/submit",
        json={"justification": "Lock it."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )

    resp = client.patch(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}",
        json={"content_text": "tampered"},
        headers=headers,
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"] == "InvalidStateError"
    assert "screenplay_locked" in resp.json()["detail"]

    audit = client.get(f"/api/v1/projects/{project['id']}/audit-log", headers=headers).json()
    assert any(e["action"] == "screenplay_locked_mutation_blocked" for e in audit)


# -- TFD-SCR-004: Script Intelligence reads one specific version --------------


def test_script_intelligence_run_records_which_screenplay_version_it_read(client, tenant):
    project = create_project(client, tenant)
    version = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"screenplay_version_id": version["id"], "sync_execution": True},
        headers=headers,
    )
    assert trigger.status_code == 200, trigger.text
    run = client.get(f"/api/v1/workflow-runs/{trigger.json()['workflow_run_id']}", headers=headers).json()
    assert run["screenplay_version_id"] == version["id"]


# -- TFD-SCR-005: suggestions workspace ----------------------------------------


def test_suggestions_are_generated_and_disposed_without_changing_the_version_hash(client, tenant):
    project = create_project(client, tenant)
    version = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    original_hash = version["content_hash"]

    generated = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}/suggestions/generate",
        json={"scope_notes": "make the opening punchier"},
        headers=headers,
    )
    assert generated.status_code == 201, generated.text
    suggestions = generated.json()
    assert len(suggestions) > 0
    assert all(s["generator_mode"] == "deterministic" for s in suggestions)

    first = suggestions[0]
    decided = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-suggestions/{first['id']}/decide",
        json={"disposition": "accepted_for_revision", "notes": "Good idea."},
        headers=headers,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["disposition"] == "accepted_for_revision"
    assert decided.json()["decided_by"] == tenant.user_id

    reread = client.get(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}", headers=headers
    ).json()
    assert reread["content_hash"] == original_hash


def test_a_suggestion_already_decided_cannot_be_decided_again(client, tenant):
    project = create_project(client, tenant)
    version = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    suggestions = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{version['id']}/suggestions/generate",
        json={},
        headers=headers,
    ).json()
    suggestion_id = suggestions[0]["id"]
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-suggestions/{suggestion_id}/decide",
        json={"disposition": "rejected"},
        headers=headers,
    )
    again = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-suggestions/{suggestion_id}/decide",
        json={"disposition": "deferred"},
        headers=headers,
    )
    assert again.status_code == 409, again.text


# -- TFD-SCR-006/007: director revision, diff, justification, management review --


def test_a_revision_is_derived_from_canonical_diffed_and_requires_justification(client, tenant):
    project = create_project(client, tenant)
    v1 = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/submit",
        json={"justification": "Initial lock."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )

    revised = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/revise", headers=headers
    )
    assert revised.status_code == 201, revised.text
    v2 = revised.json()
    assert v2["derived_from_version_id"] == v1["id"]
    assert v2["status"] == "draft"

    new_content = v1["content_text"] + "\n\nEXT. NEW SCENE - DAY\n\nA brand new scene.\n"
    updated = client.patch(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}",
        json={"content_text": new_content},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text

    diff = client.get(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/diff?against={v1['id']}",
        headers=headers,
    )
    assert diff.status_code == 200, diff.text
    assert diff.json()["lines_added"] > 0
    assert any(c["change"] == "added" for c in diff.json()["scenes_changed"])

    # AT-SCR-006.2: no justification -> 422, stays draft.
    rejected_submit = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/submit",
        json={"justification": "   "},
        headers=headers,
    )
    assert rejected_submit.status_code == 422, rejected_submit.text
    still_draft = client.get(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}", headers=headers
    ).json()
    assert still_draft["status"] == "draft"

    ok_submit = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/submit",
        json={"justification": "Adds a new establishing scene."},
        headers=headers,
    )
    assert ok_submit.status_code == 200, ok_submit.text
    assert ok_submit.json()["status"] == "in_review"


def test_management_reject_keeps_the_old_canonical_and_shows_notes(client, tenant):
    project = create_project(client, tenant)
    v1 = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/submit",
        json={"justification": "Initial lock."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    v2 = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/revise", headers=headers
    ).json()
    client.patch(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}",
        json={"content_text": v1["content_text"] + "\nmore"},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/submit",
        json={"justification": "A change."},
        headers=headers,
    )

    decided = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/decide",
        json={"decision": "rejected", "notes": "Not aligned with the brief."},
        headers=headers,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["version_status"] == "rejected"
    assert decided.json()["is_canonical"] is False

    v1_reread = client.get(f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}", headers=headers).json()
    assert v1_reread["is_production_canonical"] is True


def test_management_requesting_changes_returns_the_revision_to_draft(client, tenant):
    project = create_project(client, tenant)
    v1 = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/submit",
        json={"justification": "Initial lock."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    v2 = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/revise", headers=headers
    ).json()
    client.patch(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}",
        json={"content_text": v1["content_text"] + "\nmore"},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/submit",
        json={"justification": "A change."},
        headers=headers,
    )

    decided = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/decide",
        json={"decision": "changes_requested", "notes": "Please tighten the dialogue."},
        headers=headers,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["version_status"] == "draft"

    # Now editable again and resubmittable.
    resubmit = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/submit",
        json={"justification": "Tightened per notes."},
        headers=headers,
    )
    assert resubmit.status_code == 200, resubmit.text


# -- TFD-SCR-002.2: concurrent approvals -> exactly one canonical --------------


def test_sequential_approvals_always_leave_exactly_one_canonical_version(client, tenant):
    """Not a true concurrency test (see test_the_db_constraint_rejects_two_canonical_
    versions_at_once below for that): this confirms the service-level invariant holds
    across repeated approvals regardless of ordering -- each approval correctly
    supersedes whichever version is canonical *at that moment*, so "exactly one
    canonical" never breaks even without an actual race."""
    project = create_project(client, tenant)
    v1 = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/submit",
        json={"justification": "Initial lock."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )

    v2 = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/revise", headers=headers
    ).json()
    client.patch(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}",
        json={"content_text": v1["content_text"] + "\nv2 change"},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/submit",
        json={"justification": "v2 change."},
        headers=headers,
    )
    decided_v2 = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decided_v2.status_code == 200, decided_v2.text
    assert decided_v2.json()["is_canonical"] is True

    v3 = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/revise", headers=headers
    ).json()
    client.patch(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v3['id']}",
        json={"content_text": v2["content_text"] + "\nv3 change"},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v3['id']}/submit",
        json={"justification": "v3 change."},
        headers=headers,
    )
    decided_v3 = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v3['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    assert decided_v3.status_code == 200, decided_v3.text

    versions = client.get(f"/api/v1/projects/{project['id']}/screenplay-versions", headers=headers).json()
    canonical = [v for v in versions if v["is_production_canonical"]]
    assert len(canonical) == 1
    assert canonical[0]["id"] == v3["id"]
    v1_reread = next(v for v in versions if v["id"] == v1["id"])
    v2_reread = next(v for v in versions if v["id"] == v2["id"])
    assert v1_reread["status"] == "superseded"
    assert v2_reread["status"] == "superseded"


def test_the_db_constraint_rejects_two_canonical_versions_at_once(tenant):
    """AT-SCR-002.2's actual guarantee is a database constraint (the partial unique
    index on (project_id, episode_id) WHERE is_production_canonical), not application
    logic -- this is the deterministic way to prove it holds, since forcing two HTTP
    requests to genuinely overlap inside the same transaction window is inherently
    timing-dependent and was flaky when tried that way."""
    project_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            ProjectModel(
                id=project_id,
                organization_id=tenant.org_id,
                title="Race Test",
                current_version=1,
                created_by=tenant.user_id,
            )
        )
        db.flush()
        v1_id, v2_id = str(uuid.uuid4()), str(uuid.uuid4())
        db.add(
            ScreenplayVersionModel(
                id=v1_id,
                project_id=project_id,
                organization_id=tenant.org_id,
                version_number=1,
                status="approved_locked",
                is_production_canonical=True,
                content_text="v1",
                content_hash="x",
                created_by=tenant.user_id,
            )
        )
        db.add(
            ScreenplayVersionModel(
                id=v2_id,
                project_id=project_id,
                organization_id=tenant.org_id,
                version_number=2,
                status="in_review",
                is_production_canonical=False,
                content_text="v2",
                content_hash="y",
                created_by=tenant.user_id,
            )
        )
        db.commit()

        # The bug this constraint exists to prevent: setting a second row canonical
        # without first un-setting the first one.
        v2 = db.get(ScreenplayVersionModel, v2_id)
        v2.is_production_canonical = True
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
    finally:
        db.close()


# -- TFD-SCR-010: impact analysis -----------------------------------------------


def test_locking_a_revision_that_removes_a_scene_flags_it_for_review(client, tenant):
    project = create_project(client, tenant)
    v1 = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/submit",
        json={"justification": "Initial lock."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    # Commit the canonical scenes so there is something for impact analysis to flag.
    run = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"screenplay_version_id": v1["id"], "sync_execution": True},
        headers=headers,
    ).json()
    approval_id = run["approval_request_id"]
    client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    scenes_before = client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()
    assert len(scenes_before) >= 1
    assert all(s["screenplay_version_id"] == v1["id"] for s in scenes_before)

    # A revision that drops the second scene entirely.
    first_scene_only = v1["content_text"].split("INT. MONASTERY ARCHIVE")[0]
    v2 = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/revise", headers=headers
    ).json()
    client.patch(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}",
        json={"content_text": first_scene_only},
        headers=headers,
    )

    preview = client.get(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/impact-preview", headers=headers
    )
    assert preview.status_code == 200, preview.text
    assert len(preview.json()["affected_items"]) >= 1

    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/submit",
        json={"justification": "Cut scene 2."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )

    analyses = client.get(f"/api/v1/projects/{project['id']}/impact-analyses", headers=headers).json()
    assert len(analyses) == 1
    assert analyses[0]["new_version_id"] == v2["id"]
    assert len(analyses[0]["affected_items"]) >= 1

    scenes_after = client.get(f"/api/v1/projects/{project['id']}/scenes", headers=headers).json()
    flagged = [s for s in scenes_after if s["id"] in {i["item_id"] for i in analyses[0]["affected_items"]}]
    assert len(flagged) >= 1
    assert all(s["review_status"] == "review_required" for s in flagged)


# -- TFD-SCR-008: full history retained -----------------------------------------


def test_every_version_and_its_relationships_are_retained(client, tenant):
    project = create_project(client, tenant)
    v1 = _import_version(client, tenant, project["id"])
    headers = as_actor(tenant.user_id)
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/submit",
        json={"justification": "Initial lock."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/decide",
        json={"decision": "approved"},
        headers=headers,
    )
    v2 = client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v1['id']}/revise", headers=headers
    ).json()
    client.patch(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}",
        json={"content_text": v1["content_text"] + "\nmore"},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/submit",
        json={"justification": "A change."},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/screenplay-versions/{v2['id']}/decide",
        json={"decision": "rejected", "notes": "No."},
        headers=headers,
    )

    versions = client.get(f"/api/v1/projects/{project['id']}/screenplay-versions", headers=headers).json()
    assert {v["version_number"] for v in versions} == {1, 2}
    v2_reread = next(v for v in versions if v["id"] == v2["id"])
    assert v2_reread["status"] == "rejected"
    assert v2_reread["derived_from_version_id"] == v1["id"]
    v1_reread = next(v for v in versions if v["id"] == v1["id"])
    assert v1_reread["status"] == "approved_locked"
    assert v1_reread["is_production_canonical"] is True
