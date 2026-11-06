"""Journey staleness primitive (GW1; JOURNEY_MANIFEST.md §6 step 10).

No real D-stage trigger exists yet to mark something stale automatically (that happens
once upstream domain events exist, e.g. "screenplay version approved" -> downstream
character/shot groups go stale). This tests the PRIMITIVE itself: a staleness row makes
the affected subpoint report status "stale" regardless of its last persisted status, and
acting on that subpoint again resolves it -- the mechanism GW1 commits to, ready for a
D-stage service to call `JourneyRepository.mark_stale(...)` once it has something to.
"""

from __future__ import annotations

from packages.persistence.database import SessionLocal
from packages.persistence.repositories import JourneyRepository
from tests.support import as_actor, create_project


def _mark_stale(project_id: str, org_id: str, jrn_id: str) -> None:
    db = SessionLocal()
    try:
        JourneyRepository(db).mark_stale(
            project_id, org_id, jrn_id, reason="Upstream screenplay version changed", caused_by="test_fixture"
        )
        db.commit()
    finally:
        db.close()


def test_a_completed_item_marked_stale_reports_stale_in_the_journey_view(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    jrn = "JRN-05.3.1"

    complete = client.post(f"/api/v1/projects/{project['id']}/journey/items/{jrn}", json={"action": "complete"}, headers=headers)
    assert complete.status_code == 200, complete.text

    _mark_stale(project["id"], tenant.org_id, jrn)

    journey = client.get(f"/api/v1/projects/{project['id']}/journey", headers=headers).json()
    group = next(g for s in journey for g in s["groups"] if g["id"] == "JRN-05.3")
    subpoint = next(sp for sp in group["subpoints"] if sp["id"] == jrn)
    assert subpoint["status"] == "stale"
    assert group["status"] == "stale"


def test_acting_on_a_stale_item_resolves_the_staleness(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    jrn = "JRN-05.3.1"

    client.post(f"/api/v1/projects/{project['id']}/journey/items/{jrn}", json={"action": "complete"}, headers=headers)
    _mark_stale(project["id"], tenant.org_id, jrn)

    re_complete = client.post(f"/api/v1/projects/{project['id']}/journey/items/{jrn}", json={"action": "complete"}, headers=headers)
    assert re_complete.status_code == 200, re_complete.text
    assert re_complete.json()["status"] == "completed"

    journey = client.get(f"/api/v1/projects/{project['id']}/journey", headers=headers).json()
    subpoint = next(sp for s in journey for g in s["groups"] for sp in g["subpoints"] if sp["id"] == jrn)
    assert subpoint["status"] == "completed", "re-completing must clear the staleness, not just overwrite it visually"


def test_mark_stale_is_idempotent_and_does_not_duplicate_rows(tenant):
    db = SessionLocal()
    try:
        from packages.persistence.models import ProjectModel

        proj = ProjectModel(organization_id=tenant.org_id, title="Staleness idempotency", created_by=tenant.user_id)
        db.add(proj)
        db.flush()
        journey = JourneyRepository(db)
        journey.mark_stale(proj.id, tenant.org_id, "JRN-05.3.1", reason="first", caused_by="test")
        journey.mark_stale(proj.id, tenant.org_id, "JRN-05.3.1", reason="second call", caused_by="test")
        db.commit()
        assert journey.stale_jrn_ids(proj.id) == {"JRN-05.3.1"}

        from packages.persistence.models import JourneyStalenessModel

        rows = db.query(JourneyStalenessModel).filter_by(project_id=proj.id).all()
        assert len(rows) == 1, "a second mark_stale call on an unresolved item must not add a duplicate row"
    finally:
        db.close()
