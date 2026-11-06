"""Background worker: claims durable outbox tasks and executes workflow runs.

Lease/retry/dead-letter (C6; docs/audit/08 PERF-04): a task's claim has a time-bounded
lease. If this process dies mid-task, no separate recovery process is needed -- the next
``claim_next`` call (from this process or another) will notice the lease expired and
reclaim it. A failed attempt is backed off with exponential delay plus full jitter and
re-queued, up to ``max_attempts``, after which it is dead-lettered and never retried
again automatically.

Run with: ``python -m apps.worker.worker``
"""

from __future__ import annotations

import random
import time
from datetime import timedelta
from typing import Callable, Dict

from packages.core.config import Settings, get_settings
from packages.core.logging import configure_logging, get_logger
from packages.domain.enums import (
    FILM_BIBLE_GRAPH_ID,
    HISTORICAL_RESEARCH_GRAPH_ID,
    SCRIPT_INTELLIGENCE_GRAPH_ID,
    STORYBOARD_INTELLIGENCE_GRAPH_ID,
)
from packages.domain.errors import DomainInvariantError
from packages.persistence.database import session_scope
from packages.persistence.models import OutboxTaskModel
from packages.persistence.repositories import OutboxRepository, utc_now
from packages.services.film_bible import FilmBibleSynthesisService
from packages.services.historical_research import HistoricalResearchService
from packages.services.script_intelligence import ScriptIntelligenceService
from packages.services.storyboard import StoryboardIntelligenceService
from packages.workflows.checkpointer import setup_checkpointer_schema

logger = get_logger("worker")


def _run_script_intelligence(workflow_run_id: str) -> None:
    with session_scope() as db:
        ScriptIntelligenceService(db).execute(workflow_run_id)


def _run_historical_research(workflow_run_id: str) -> None:
    with session_scope() as db:
        HistoricalResearchService(db).execute(workflow_run_id)


def _run_storyboard_intelligence(workflow_run_id: str) -> None:
    with session_scope() as db:
        StoryboardIntelligenceService(db).execute(workflow_run_id)


def _run_film_bible(workflow_run_id: str) -> None:
    with session_scope() as db:
        FilmBibleSynthesisService(db).execute(workflow_run_id)


TASK_HANDLERS: Dict[str, Callable[[str], None]] = {
    SCRIPT_INTELLIGENCE_GRAPH_ID: _run_script_intelligence,
    HISTORICAL_RESEARCH_GRAPH_ID: _run_historical_research,
    STORYBOARD_INTELLIGENCE_GRAPH_ID: _run_storyboard_intelligence,
    FILM_BIBLE_GRAPH_ID: _run_film_bible,
}


def _backoff_delay(attempts: int, settings: Settings) -> timedelta:
    """Exponential backoff with full jitter, capped. ``attempts`` is already >= 1 (set
    by claim_next before the task is handed to a handler)."""
    cap = settings.worker_backoff_max_seconds
    ceiling = min(cap, settings.worker_backoff_base_seconds * (2 ** (attempts - 1)))
    return timedelta(seconds=random.uniform(0, ceiling))  # noqa: S311  jitter, not crypto


def _finish_task_ok(task_id: str) -> None:
    with session_scope() as db:
        OutboxRepository(db).mark_completed(task_id)
        db.commit()


def _finish_task_failed(task_id: str, exc: Exception, settings: Settings) -> None:
    with session_scope() as db:
        outbox = OutboxRepository(db)

        if isinstance(exc, DomainInvariantError):
            # A business-rule violation (bad input, missing permission, stale version...)
            # will fail identically on every retry: the input doesn't change between
            # attempts. Retrying it max_attempts times with backoff would only delay a
            # result the system already knows, so skip straight to dead-lettered.
            task = outbox.dead_letter_immediately(
                task_id, error_class=type(exc).__name__, error_message=str(exc)[:2000]
            )
            db.commit()
            logger.error(
                "Task %s dead-lettered immediately (non-retryable %s: %s)",
                task_id, type(exc).__name__, exc,
            )
            return

        existing = db.get(OutboxTaskModel, task_id)
        attempts = existing.attempts if existing is not None else 1
        task = outbox.retry_or_dead_letter(
            task_id,
            error_class=type(exc).__name__,
            error_message=str(exc)[:2000],
            next_attempt_at=utc_now() + _backoff_delay(attempts, settings),
        )
        db.commit()
        if task.status == "dead_lettered":
            logger.error(
                "Task %s dead-lettered after %s attempts (last error: %s: %s)",
                task_id, task.attempts, type(exc).__name__, exc,
            )
        else:
            logger.warning(
                "Task %s failed (attempt %s/%s); retrying at %s (%s: %s)",
                task_id, task.attempts, task.max_attempts, task.next_attempt_at, type(exc).__name__, exc,
            )


def process_one_task(worker_id: str | None = None) -> bool:
    """Claim and process a single outbox task. Returns True if a task was claimed."""
    settings = get_settings()
    worker_id = worker_id or settings.worker_id
    with session_scope() as db:
        task = OutboxRepository(db).claim_next(worker_id, lease_seconds=settings.worker_lease_seconds)
        if task is None:
            return False
        task_id, task_type, run_id = task.id, task.task_type, task.workflow_run_id
        db.commit()

    logger.info("Claimed task %s (type=%s, run=%s)", task_id, task_type, run_id)
    handler = TASK_HANDLERS.get(task_type)
    if handler is None:
        logger.error("No handler for task type %r (task %s); dead-lettering", task_type, task_id)
        _finish_task_failed(task_id, ValueError(f"no handler registered for task_type={task_type!r}"), settings)
        return True

    try:
        handler(run_id)
    except Exception as exc:
        # The service has already marked the workflow run failed and logged the cause;
        # this records the outbox-level retry/dead-letter decision.
        logger.exception("Task %s failed", task_id)
        _finish_task_failed(task_id, exc, settings)
        return True

    _finish_task_ok(task_id)
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
    setup_checkpointer_schema()
    run_worker_loop()
