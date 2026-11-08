"""C6: outbox_tasks allows several tasks per run over time, but only one active at once."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from packages.domain.enums import OutboxStatus
from packages.persistence.database import SessionLocal
from packages.persistence.repositories import OutboxRepository
from tests.support import project_with_pending_approval


def _run_id(client, tenant) -> str:
    _, workflow = project_with_pending_approval(client, tenant)
    return workflow["workflow_run_id"]


@pytest.mark.parametrize("finished", [OutboxStatus.COMPLETED.value, OutboxStatus.DEAD_LETTERED.value])
def test_a_run_can_get_a_new_task_after_the_previous_one_finished(client, tenant, finished):
    run_id = _run_id(client, tenant)
    db = SessionLocal()
    try:
        outbox = OutboxRepository(db)
        first = outbox.enqueue(run_id, "script_intelligence", {})
        first.status = finished
        db.commit()
        second = outbox.enqueue(run_id, "script_intelligence", {"retry": True})
        db.commit()
        assert second.id != first.id
    finally:
        db.close()


@pytest.mark.parametrize("active", [OutboxStatus.PENDING.value, OutboxStatus.CLAIMED.value])
def test_two_active_tasks_for_one_run_are_rejected(client, tenant, active):
    run_id = _run_id(client, tenant)
    db = SessionLocal()
    try:
        outbox = OutboxRepository(db)
        first = outbox.enqueue(run_id, "script_intelligence", {})
        first.status = active
        db.commit()
        with pytest.raises(IntegrityError):
            outbox.enqueue(run_id, "script_intelligence", {"duplicate": True})
            db.commit()
        db.rollback()
    finally:
        db.close()
