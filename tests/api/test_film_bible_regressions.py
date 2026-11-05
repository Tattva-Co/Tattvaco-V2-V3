"""Regression tests for the G-04 (Film Bible) defects fixed in milestone C1.

See docs/audit/02_FEATURE_IMPLEMENTATION_MATRIX.md §4 (G04-A…I).
"""

from __future__ import annotations

import uuid

from packages.persistence.database import SessionLocal
from packages.persistence.models import ResearchClaimModel, UserModel, WorkflowRunModel
from tests.support import as_actor, create_project


def _add_reviewer(org_id: str) -> str:
    """Create a second user in the same organization to act as reviewer."""
    user_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            UserModel(
                id=user_id,
                organization_id=org_id,
                email=f"{user_id[:8]}@reviewer.example",
                full_name="Reviewer",
                role="director",
            )
        )
        db.commit()
    finally:
        db.close()
    return user_id


def _start_synthesis(client, tenant, project_id: str) -> str:
    resp = client.post(
        f"/api/v1/projects/{project_id}/workflows/film-bible-synthesis",
        json={"sync_execution": True},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "awaiting_approval"
    return resp.json()["approval_request_id"]


def test_decision_notes_reach_canon_and_reviewer_is_attributed(client, tenant):
    """G04-A (notes dropped), G04-H (version field overwritten), G04-I (initiator overwritten)."""
    project = create_project(client, tenant, title="Attribution Check")
    reviewer_id = _add_reviewer(tenant.org_id)
    approval_id = _start_synthesis(client, tenant, project["id"])

    resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "approved", "notes": "Keep the ochre palette strict"},
        headers=as_actor(reviewer_id),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["new_project_version"] == 2

    rules = client.get(
        f"/api/v1/projects/{project['id']}/film-bible/rules", headers=as_actor(tenant.user_id)
    ).json()
    assert rules, "approval without a selection must commit every candidate"
    assert all("Keep the ochre palette strict" in (r["rationale"] or "") for r in rules)

    versions = client.get(
        f"/api/v1/projects/{project['id']}/versions", headers=as_actor(tenant.user_id)
    ).json()
    v2 = next(v for v in versions if v["version_number"] == 2)
    assert v2["committed_by"] == reviewer_id
    assert "Keep the ochre palette strict" in v2["commit_message"]

    db = SessionLocal()
    try:
        run = db.query(WorkflowRunModel).filter_by(project_id=project["id"]).one()
        assert run.actor_id == tenant.user_id, "initiator must not be replaced by the reviewer"
        assert run.expected_project_version == 1, "start version must not be overwritten"
        assert run.status == "completed"
    finally:
        db.close()


def test_empty_selection_commits_nothing(client, tenant):
    """An explicit empty selection approves no rules (None means all, [] means none)."""
    project = create_project(client, tenant, title="Empty Selection")
    approval_id = _start_synthesis(client, tenant, project["id"])

    resp = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "approved", "approved_rule_ids": []},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 200, resp.text
    rules = client.get(
        f"/api/v1/projects/{project['id']}/film-bible/rules", headers=as_actor(tenant.user_id)
    ).json()
    assert rules == []


def test_manual_rule_rejects_unknown_category_and_strictness(client, tenant):
    project = create_project(client, tenant, title="Validation")
    url = f"/api/v1/projects/{project['id']}/film-bible/rules"
    base = {"title": "T", "rule_text": "R"}

    bad_category = client.post(
        url, json={**base, "category": "not_a_category"}, headers=as_actor(tenant.user_id)
    )
    assert bad_category.status_code == 422

    bad_strictness = client.post(
        url,
        json={**base, "category": "color_palette", "strictness": "sometimes"},
        headers=as_actor(tenant.user_id),
    )
    assert bad_strictness.status_code == 422


def test_manual_rule_cannot_reference_another_tenants_claim(client, tenant, other_tenant):
    """A foreign historical_claim_id must not be linkable (cross-tenant reference)."""
    foreign_project = create_project(client, other_tenant, title="Foreign")
    claim_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            ResearchClaimModel(
                id=claim_id,
                project_id=foreign_project["id"],
                organization_id=other_tenant.org_id,
                project_version=1,
                claim_class="historical_fact",
                statement="Foreign claim",
            )
        )
        db.commit()
    finally:
        db.close()

    project = create_project(client, tenant, title="Mine")
    resp = client.post(
        f"/api/v1/projects/{project['id']}/film-bible/rules",
        json={
            "category": "color_palette",
            "title": "T",
            "rule_text": "R",
            "historical_claim_id": claim_id,
        },
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 404
