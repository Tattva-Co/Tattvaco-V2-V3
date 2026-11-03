"""Background worker process for processing durable outbox tasks."""

from datetime import datetime, timezone
import logging
import os
import time
from typing import Optional

from sqlalchemy.orm import Session

from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    AssetModel,
    OutboxTaskModel,
    ProjectModel,
    WorkflowRunModel,
)
from packages.storage.service import LocalFileSystemStorageService
from packages.workflows.checkpointer import get_checkpointer
from packages.workflows.script_intelligence.graph import build_script_intelligence_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tattva-worker")

storage = LocalFileSystemStorageService(root_dir=os.getenv("STORAGE_LOCAL_ROOT", "./data/storage"))


def process_one_task(db: Session, worker_id: str = "worker-1") -> bool:
    """Claim and process a single outbox task. Returns True if a task was processed."""
    task = (
        db.query(OutboxTaskModel)
        .filter_by(status="pending")
        .with_for_update(skip_locked=True)
        .first()
    )
    if not task:
        return False

    task.status = "claimed"
    task.claimed_by = worker_id
    task.claimed_at = datetime.now(timezone.utc)
    task.attempts += 1
    db.commit()

    logger.info(f"Claimed task {task.id} (type: {task.task_type}) for run {task.workflow_run_id}")

    try:
        if task.task_type == "script_intelligence":
            payload = task.payload
            project_id = payload["project_id"]
            script_asset_id = payload["script_asset_id"]
            actor_id = payload.get("actor_id")

            project = db.query(ProjectModel).filter_by(id=project_id).first()
            asset = db.query(AssetModel).filter_by(id=script_asset_id).first()

            if not project or not asset:
                raise ValueError(f"Project or Asset not found for task {task.id}")

            raw_content = storage.get_bytes(asset.storage_path).decode("utf-8", errors="replace")

            with get_checkpointer() as checkpointer:
                graph = build_script_intelligence_graph().compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": task.workflow_run_id}}
                initial_state = {
                    "workflow_run_id": task.workflow_run_id,
                    "project_id": project.id,
                    "organization_id": project.organization_id,
                    "actor_id": actor_id or project.created_by,
                    "expected_project_version": project.current_version,
                    "script_asset_id": asset.id,
                    "raw_script_text": raw_content,
                    "approval_status": "pending",
                }
                # Runs up to the approval interrupt node
                graph.invoke(initial_state, config=config)

        task.status = "completed"
        db.commit()
        logger.info(f"Completed task {task.id}")
        return True

    except Exception as exc:
        logger.exception(f"Error processing task {task.id}: {exc}")
        task.status = "failed"
        run = db.query(WorkflowRunModel).filter_by(id=task.workflow_run_id).first()
        if run:
            run.status = "failed"
            run.error_message = str(exc)
        db.commit()
        return False


def run_worker_loop(poll_interval: float = 1.0, max_iterations: Optional[int] = None):
    """Run worker daemon loop."""
    logger.info(f"Starting Tattva background worker (poll interval: {poll_interval}s)...")
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        iterations += 1
        db = SessionLocal()
        try:
            processed = process_one_task(db)
            if not processed:
                time.sleep(poll_interval)
        finally:
            db.close()


if __name__ == "__main__":
    run_worker_loop()
