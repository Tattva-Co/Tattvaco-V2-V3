"""C6 regression: re-executing a run that already made progress must not duplicate work.

Before this fix, *Service.execute() always built a fresh initial state and invoked the
graph with it, regardless of whether a checkpoint already existed. A worker that crashed
after a run had already written its candidates and approval request -- but before the
outbox task was marked complete -- would be redelivered the same task, re-run the whole
graph from scratch, and duplicate every candidate row and create a second approval
request for the same run (docs/audit/02: "propose_* has no idempotency").
"""

from __future__ import annotations

from packages.persistence.database import SessionLocal
from packages.persistence.models import ApprovalRequestModel, EntityCandidateModel, SceneCandidateModel
from packages.services.script_intelligence import ScriptIntelligenceService
from tests.support import as_actor, create_project, import_screenplay_version, upload_script


def test_redelivered_script_intelligence_task_does_not_duplicate_candidates(client, tenant):
    project = create_project(client, tenant)
    upload = upload_script(client, tenant, project["id"])
    assert upload.status_code == 200, upload.text
    version = import_screenplay_version(client, tenant, project["id"], upload.json()["asset_id"])

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"screenplay_version_id": version["id"], "sync_execution": False},
        headers=as_actor(tenant.user_id),
    )
    assert trigger.status_code == 200, trigger.text
    run_id = trigger.json()["workflow_run_id"]

    # First execution: as the worker would do it.
    db = SessionLocal()
    try:
        ScriptIntelligenceService(db).execute(run_id)
    finally:
        db.close()

    scenes_after_first = _count(SceneCandidateModel, run_id)
    entities_after_first = _count(EntityCandidateModel, run_id)
    approvals_after_first = _count(ApprovalRequestModel, run_id)
    assert scenes_after_first > 0
    assert approvals_after_first == 1

    # Simulated redelivery: the same outbox task claimed again (e.g. after a stale-lease
    # sweep believed the first worker had crashed).
    db = SessionLocal()
    try:
        ScriptIntelligenceService(db).execute(run_id)
    finally:
        db.close()

    assert _count(SceneCandidateModel, run_id) == scenes_after_first
    assert _count(EntityCandidateModel, run_id) == entities_after_first
    assert _count(ApprovalRequestModel, run_id) == approvals_after_first == 1


def _count(model, run_id: str) -> int:
    db = SessionLocal()
    try:
        return db.query(model).filter_by(workflow_run_id=run_id).count()
    finally:
        db.close()
