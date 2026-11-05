"""Regression test for PERF-06 (docs/audit/08): the project-version race.

Two independent workflow runs (historical research, storyboard) are both started
while the project is at version 1, so both capture ``expected_project_version=1``.
Approving them concurrently must not let both believe they are "the" version-2 commit:
exactly one succeeds and advances the project to version 2; the other must see that its
assumed starting version is stale and fail with a version conflict (409), never silently
commit a duplicate ``project_versions`` row at version 2.

Before the C4 fix (project-row FOR UPDATE lock in commit_approved_candidates), both
committers read current_version=1 unlocked, both computed new_version=2, and both wrote
a project_versions row with version_number=2.
"""

from __future__ import annotations

import threading

from tests.support import as_actor, create_project


def _trigger(client, tenant, project_id: str, workflow: str, payload: dict) -> str:
    resp = client.post(
        f"/api/v1/projects/{project_id}/workflows/{workflow}",
        json={**payload, "sync_execution": True},
        headers=as_actor(tenant.user_id),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "awaiting_approval", body
    return body["approval_request_id"]


def test_concurrent_approvals_on_the_same_project_do_not_duplicate_the_version(client, tenant):
    project = create_project(client, tenant, title="Concurrency Check")
    headers = as_actor(tenant.user_id)

    research_approval_id = _trigger(
        client, tenant, project["id"], "historical-research", {"topic": "Kalinga fortifications"}
    )
    storyboard_approval_id = _trigger(
        client, tenant, project["id"], "storyboard-intelligence", {"brief": "Opening battle sequence"}
    )

    results: dict[str, object] = {}

    def decide(key: str, approval_id: str) -> None:
        resp = client.post(
            f"/api/v1/approvals/{approval_id}/decide",
            json={"decision": "approved"},
            headers=headers,
        )
        results[key] = (resp.status_code, resp.json())

    t1 = threading.Thread(target=decide, args=("research", research_approval_id))
    t2 = threading.Thread(target=decide, args=("storyboard", storyboard_approval_id))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    statuses = sorted(status for status, _ in results.values())
    # Exactly one commit must succeed at the single available version-2 slot; the other,
    # whichever run it is, must be told its assumed starting version is stale.
    assert statuses == [200, 409], results

    winner_body = next(body for status, body in results.values() if status == 200)
    assert winner_body["new_project_version"] == 2

    project_now = client.get(f"/api/v1/projects/{project['id']}", headers=headers).json()
    assert project_now["current_version"] == 2

    versions = client.get(f"/api/v1/projects/{project['id']}/versions", headers=headers).json()
    version_numbers = [v["version_number"] for v in versions]
    assert version_numbers.count(2) == 1, (
        f"expected exactly one version-2 row, got {version_numbers.count(2)}: {version_numbers}"
    )
