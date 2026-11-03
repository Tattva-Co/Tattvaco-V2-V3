"""Background worker: claims durable outbox tasks and executes workflow runs.

Run with: ``python -m apps.worker.worker``
"""

from __future__ import annotations

import time
from typing import Callable, Dict

from packages.core.config import get_settings
from packages.core.logging import configure_logging, get_logger
from packages.domain.enums import SCRIPT_INTELLIGENCE_GRAPH_ID, OutboxStatus
from packages.persistence.database import session_scope
from packages.persistence.models import OutboxTaskModel
from packages.persistence.repositories import OutboxRepository
from packages.services.script_intelligence import ScriptIntelligenceService

logger = get_logger("worker")


def _run_script_intelligence(workflow_run_id: str) -> None:
    with session_scope() as db:
        ScriptIntelligenceService(db).execute(workflow_run_id)


TASK_HANDLERS: Dict[str, Callable[[str], None]] = {
    SCRIPT_INTELLIGENCE_GRAPH_ID: _run_script_intelligence,
}


def _finish_task(task_id: str, status: OutboxStatus) -> None:
    with session_scope() as db:
        task = db.get(OutboxTaskModel, task_id)
        if task is not None:
            task.status = status.value
            db.commit()


def process_one_task(worker_id: str | None = None) -> bool:
    """Claim and process a single outbox task. Returns True if a task was claimed."""
    worker_id = worker_id or get_settings().worker_id
    with session_scope() as db:
        task = OutboxRepository(db).claim_next(worker_id)
        if task is None:
            return False
        task_id, task_type, run_id = task.id, task.task_type, task.workflow_run_id
        db.commit()

    logger.info("Claimed task %s (type=%s, run=%s)", task_id, task_type, run_id)
    handler = TASK_HANDLERS.get(task_type)
    if handler is None:
        logger.error("No handler for task type %r (task %s)", task_type, task_id)
        _finish_task(task_id, OutboxStatus.FAILED)
        return True

    try:
        handler(run_id)
    except Exception:
        # The service has already marked the workflow run failed and logged the cause.
        logger.exception("Task %s failed", task_id)
        _finish_task(task_id, OutboxStatus.FAILED)
        return True

    _finish_task(task_id, OutboxStatus.COMPLETED)
    logger.info("Completed task %s", task_id)
    return True


def run_worker_loop(poll_interval: float | None = None, max_iterations: int | None = None) -> None:
    settings = get_settings()
    poll_interval = settings.worker_poll_interval_seconds if poll_interval is None else poll_interval
    logger.info("Starting Tattva worker %s (poll interval %.1fs)", settings.worker_id, poll_interval)
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        iterations += 1
        if not process_one_task(settings.worker_id):
            time.sleep(poll_interval)


if __name__ == "__main__":
    configure_logging(get_settings().log_level)
    run_worker_loop()
