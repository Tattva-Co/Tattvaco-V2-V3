"""Cross-tenant negative tests at the API boundary (Build Plan risk: cross-project leakage)."""

from tests.support import as_actor, create_project, project_with_pending_approval


def test_unknown_actor_is_unauthenticated(client):
    resp = client.get("/api/v1/projects", headers=as_actor("not-a-user"))
    assert resp.status_code == 401
    assert resp.json()["error"] == "AuthenticationError"


def test_project_list_is_scoped_to_actor_organization(client, tenant, other_tenant):
    mine = create_project(client, tenant, title="Mine")
    theirs = create_project(client, other_tenant, title="Theirs")

    ids = {p["id"] for p in client.get("/api/v1/projects", headers=as_actor(tenant.user_id)).json()}
    assert mine["id"] in ids
    assert theirs["id"] not in ids


def test_foreign_project_and_children_are_invisible(client, tenant, other_tenant):
    project = create_project(client, tenant)
    intruder = as_actor(other_tenant.user_id)

    for path in ("", "/assets", "/scenes", "/entities", "/versions", "/audit-log", "/candidates"):
        resp = client.get(f"/api/v1/projects/{project['id']}{path}", headers=intruder)
        assert resp.status_code == 404, path


def test_foreign_actor_cannot_decide_approval(client, tenant, other_tenant):
    project, workflow = project_with_pending_approval(client, tenant)

    resp = client.post(
        f"/api/v1/approvals/{workflow['approval_request_id']}/decide",
        json={"decision": "approved"},
        headers=as_actor(other_tenant.user_id),
    )
    assert resp.status_code == 404

    approvals = client.get(
        f"/api/v1/projects/{project['id']}/candidates", headers=as_actor(tenant.user_id)
    ).json()["approvals"]
    assert approvals[0]["status"] == "pending"


def test_foreign_actor_cannot_read_workflow_run(client, tenant, other_tenant):
    _, workflow = project_with_pending_approval(client, tenant)
    resp = client.get(
        f"/api/v1/workflow-runs/{workflow['workflow_run_id']}", headers=as_actor(other_tenant.user_id)
    )
    assert resp.status_code == 404
