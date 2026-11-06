"""C6: outbox lease reclaim and retry/backoff (docs/audit/08 PERF-04).

Unit-level, directly against OutboxRepository, rather than through the worker's full
claim -> handler -> finish cycle: these tests are about the queue's own state machine
(a stale claim becomes reclaimable; a failed attempt backs off then eventually dead-
letters), which doesn't need a real workflow run behind it.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from packages.persistence.database import SessionLocal
from packages.persistence.models import ProjectModel, WorkflowRunModel
from packages.persistence.repositories import OutboxRepository, utc_now
from tests.support import create_tenant, purge_organization


def _enqueue_task(db, tenant, *, max_attempts: int = 3) -> tuple[str, str]:
    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    db.add(ProjectModel(id=project_id, organization_id=tenant.org_id, title="T", created_by=tenant.user_id))
    db.flush()
    db.add(
        WorkflowRunModel(
            id=run_id,
            graph_id="script_intelligence",
            graph_version="1.0",
            project_id=project_id,
            organization_id=tenant.org_id,
            actor_id=tenant.user_id,
            expected_project_version=1,
            status="queued",
        )
    )
    db.flush()
    task = OutboxRepository(db).enqueue(run_id, "script_intelligence", {}, max_attempts=max_attempts)
    db.commit()
    return task.id, run_id


def test_a_fresh_task_is_claimable_immediately():
    tenant = create_tenant()
    db = SessionLocal()
    try:
        task_id, _ = _enqueue_task(db, tenant)
        claimed = OutboxRepository(db).claim_next("worker-a", lease_seconds=300)
        assert claimed is not None
        assert claimed.id == task_id
        assert claimed.status == "claimed"
        assert claimed.attempts == 1
        assert claimed.lease_expires_at > utc_now()
        db.commit()
    finally:
        db.close()
        purge_organization(tenant.org_id)


def test_a_claimed_task_is_not_reclaimable_before_its_lease_expires():
    tenant = create_tenant()
    db = SessionLocal()
    try:
        _enqueue_task(db, tenant)
        first = OutboxRepository(db).claim_next("worker-a", lease_seconds=300)
        assert first is not None
        db.commit()

        second = OutboxRepository(db).claim_next("worker-b", lease_seconds=300)
        assert second is None, "a live lease must not be stolen by another worker"
    finally:
        db.close()
        purge_organization(tenant.org_id)


def test_a_crashed_workers_expired_lease_is_reclaimed_with_no_separate_sweep():
    tenant = create_tenant()
    db = SessionLocal()
    try:
        task_id, _ = _enqueue_task(db, tenant)
        first = OutboxRepository(db).claim_next("worker-a", lease_seconds=300)
        assert first is not None
        # Simulate worker-a crashing: force its lease into the past directly, exactly as
        # time alone would eventually do.
        first.lease_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

        reclaimed = OutboxRepository(db).claim_next("worker-b", lease_seconds=300)
        assert reclaimed is not None
        assert reclaimed.id == task_id
        assert reclaimed.claimed_by == "worker-b"
        assert reclaimed.attempts == 2, "reclaiming counts as a new attempt"
        db.commit()
    finally:
        db.close()
        purge_organization(tenant.org_id)


def test_a_failed_attempt_backs_off_and_is_retried_before_exhausting_max_attempts():
    tenant = create_tenant()
    db = SessionLocal()
    try:
        task_id, _ = _enqueue_task(db, tenant, max_attempts=3)
        outbox = OutboxRepository(db)
        claimed = outbox.claim_next("worker-a", lease_seconds=300)
        assert claimed.attempts == 1
        db.commit()

        failed = outbox.retry_or_dead_letter(
            task_id, error_class="RuntimeError", error_message="transient", next_attempt_at=utc_now() + timedelta(seconds=30)
        )
        assert failed.status == "pending", "attempts remain, so it goes back to the queue, not dead-lettered"
        assert failed.last_error_class == "RuntimeError"
        db.commit()

        # Not due yet: must not be claimable before its backoff delay elapses.
        assert outbox.claim_next("worker-b", lease_seconds=300) is None

        # Make it due and confirm it is claimed again, with the attempt count rising.
        task = db.get(type(claimed), task_id)
        task.next_attempt_at = utc_now() - timedelta(seconds=1)
        db.commit()
        reclaimed = outbox.claim_next("worker-b", lease_seconds=300)
        assert reclaimed is not None
        assert reclaimed.attempts == 2
        db.commit()
    finally:
        db.close()
        purge_organization(tenant.org_id)


def test_dead_lettered_after_max_attempts_and_never_reclaimed_again():
    tenant = create_tenant()
    db = SessionLocal()
    try:
        task_id, _ = _enqueue_task(db, tenant, max_attempts=2)
        outbox = OutboxRepository(db)

        # Attempt 1: fails, attempts remain (2 allowed), so it retries.
        claimed = outbox.claim_next("worker-a", lease_seconds=300)
        assert claimed.attempts == 1
        db.commit()
        outbox.retry_or_dead_letter(
            task_id, error_class="RuntimeError", error_message="still broken", next_attempt_at=utc_now() - timedelta(seconds=1)
        )
        db.commit()

        # Attempt 2: fails again; attempts (2) now meets max_attempts (2) -> dead-letter.
        claimed2 = outbox.claim_next("worker-a", lease_seconds=300)
        assert claimed2.attempts == 2
        db.commit()
        final = outbox.retry_or_dead_letter(
            task_id, error_class="RuntimeError", error_message="still broken", next_attempt_at=utc_now() + timedelta(seconds=1)
        )
        assert final.status == "dead_lettered"
        assert final.dead_lettered_at is not None
        db.commit()

        # A dead-lettered task is never reclaimed, no matter how long it waits.
        assert outbox.claim_next("worker-b", lease_seconds=300) is None
    finally:
        db.close()
        purge_organization(tenant.org_id)


def test_dead_letter_immediately_skips_the_retry_loop_entirely():
    tenant = create_tenant()
    db = SessionLocal()
    try:
        task_id, _ = _enqueue_task(db, tenant, max_attempts=5)
        outbox = OutboxRepository(db)
        claimed = outbox.claim_next("worker-a", lease_seconds=300)
        assert claimed.attempts == 1
        db.commit()

        result = outbox.dead_letter_immediately(
            task_id, error_class="ValidationFailure", error_message="wrong file type"
        )
        assert result.status == "dead_lettered"
        assert result.attempts == 1, "dead-lettered on the first attempt, not after exhausting max_attempts"
        db.commit()

        assert outbox.claim_next("worker-b", lease_seconds=300) is None
    finally:
        db.close()
        purge_organization(tenant.org_id)
