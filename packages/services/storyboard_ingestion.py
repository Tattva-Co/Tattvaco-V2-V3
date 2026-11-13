"""Storyboard image/PDF ingestion (D6, TFD-SB-001).

Deliberately not a LangGraph workflow: rendering PDF pages into crop assets is
deterministic, synchronous image processing (the same category of work as C7's
extraction pipeline, packages/services/extraction.py), not multi-step AI reasoning
needing an interrupt/resume checkpoint. A `workflow_runs` row is still created so
ingested panels go through the exact same review-tray/audit machinery as an
AI-generated run, but `decide()` here commits directly -- it never invokes a graph.
See `packages.services.storyboard.StoryboardService` for the many-to-many panel<->scene
mapping (TFD-SB-003), which applies to any panel, not only an ingested one.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import List

from sqlalchemy.orm import Session

from packages.domain.enums import ApprovalDecision, ApprovalStatus, AuditAction, WorkflowStatus
from packages.domain.errors import InvalidStateError, ValidationFailure
from packages.persistence.models import (
    ApprovalRequestModel,
    AssetModel,
    StoryboardPanelCandidateModel,
    WorkflowRunModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AssetRepository,
    AuditRepository,
    CandidateRepository,
    ProjectRepository,
    WorkflowRunRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext
from packages.services.script_review import record_decision
from packages.services.storyboard import StoryboardDecisionResult
from packages.services.storyboard_review import StoryboardReviewService
from packages.storage.service import StorageService

STORYBOARD_INGESTION_GRAPH_ID = "storyboard_ingestion"
STORYBOARD_INGESTION_APPROVAL_SCOPE = "storyboard_ingestion_candidates"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class StoryboardIngestionService:
    def __init__(self, db: Session, storage: StorageService):
        self.db = db
        self.storage = storage
        self.projects = ProjectRepository(db)
        self.assets = AssetRepository(db)
        self.runs = WorkflowRunRepository(db)
        self.candidates = CandidateRepository(db)
        self.approvals = ApprovalRepository(db)
        self.authz = AuthzService(db)
        self.audit = AuditRepository(db)

    def ingest_pdf(self, actor: ActorContext, project_id: str, source_asset_id: str) -> WorkflowRunModel:
        import pypdfium2 as pdfium

        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "workflow.run", project)
        source_asset = self.assets.get_for_project(source_asset_id, project.id)
        if source_asset.scan_status != "clean":
            raise ValidationFailure(f"Asset '{source_asset_id}' is not usable yet (scan_status={source_asset.scan_status!r}).")

        content = self.storage.get_bytes(source_asset.storage_path)

        run = self.runs.add(
            WorkflowRunModel(
                graph_id=STORYBOARD_INGESTION_GRAPH_ID,
                graph_version="1.0",
                project_id=project.id,
                organization_id=project.organization_id,
                actor_id=actor.user_id,
                expected_project_version=project.current_version,
                status=WorkflowStatus.RUNNING.value,
                input_asset_ids=[source_asset_id],
                output_refs={},
                generator_mode="deterministic",
            )
        )
        self.db.flush()

        candidate_rows: List[StoryboardPanelCandidateModel] = []
        page_errors: List[dict] = []
        try:
            pdf = pdfium.PdfDocument(content)
            page_count = len(pdf)
        except Exception as exc:  # noqa: BLE001 - a malformed PDF is reported, not raised
            self._mark_failed(run.id, f"Could not open PDF: {exc}")
            raise ValidationFailure(f"'{source_asset.filename}' could not be opened as a PDF: {exc}") from exc

        for page_index in range(page_count):
            page_number = page_index + 1
            try:
                page = pdf[page_index]
                bitmap = page.render(scale=1.5)
                image = bitmap.to_pil()
                buf = io.BytesIO()
                image.save(buf, format="PNG")
                stored = self.storage.store_bytes(
                    buf.getvalue(),
                    filename=f"{source_asset.filename}-page-{page_number}.png",
                    project_id=project.id,
                    organization_id=project.organization_id,
                    mime_type="image/png",
                )
                crop_asset = self.assets.add(
                    AssetModel(
                        project_id=project.id,
                        organization_id=project.organization_id,
                        filename=stored.filename,
                        mime_type=stored.mime_type,
                        size_bytes=stored.size_bytes,
                        checksum_sha256=stored.checksum_sha256,
                        storage_path=stored.storage_path,
                        asset_type="image",
                        is_original=False,
                        parent_asset_id=source_asset.id,
                        uploaded_by=actor.user_id,
                        scan_status="clean",  # server-rendered from an already-clean PDF, not user-supplied
                    )
                )
                self.db.flush()

                row = StoryboardPanelCandidateModel(
                    workflow_run_id=run.id,
                    project_id=project.id,
                    organization_id=project.organization_id,
                    panel_number=page_number,
                    description=f"Storyboard page {page_number} of '{source_asset.filename}'",
                    status="proposed",
                    generator_mode="deterministic",
                    source="ingested",
                    page_locator=f"Page {page_number}",
                    crop_asset_id=crop_asset.id,
                )
                self.candidates.add_storyboard_panel(row)
                candidate_rows.append(row)
            except Exception as exc:  # noqa: BLE001 - AT-SB-001.1: one bad page is reported, the rest still succeed
                page_errors.append({"page": page_number, "error": str(exc)})

        approval = self.approvals.add(
            ApprovalRequestModel(
                workflow_run_id=run.id,
                project_id=project.id,
                organization_id=project.organization_id,
                scope=STORYBOARD_INGESTION_APPROVAL_SCOPE,
                candidate_summary={
                    "panel_count": len(candidate_rows),
                    "page_errors": page_errors,
                    "panels": [{"id": r.id, "panel_number": r.panel_number, "page_locator": r.page_locator} for r in candidate_rows],
                },
                status=ApprovalStatus.PENDING.value,
            )
        )
        run.status = WorkflowStatus.AWAITING_APPROVAL.value
        run.output_refs = {"page_count": page_count, "panel_count": len(candidate_rows), "page_errors": page_errors}

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.STORYBOARD_INGESTION_STARTED,
            target_type="approval_request",
            target_id=approval.id,
            details={"source_asset_id": source_asset_id, "panel_count": len(candidate_rows), "page_errors": page_errors},
        )
        self.db.commit()
        return self.runs.get(run.id)

    def _mark_failed(self, run_id: str, error_message: str) -> None:
        run = self.runs.get(run_id)
        if run is not None:
            run.status = WorkflowStatus.FAILED.value
            run.error_message = error_message
            self.db.commit()

    def decide(
        self,
        actor: ActorContext,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        notes: str | None = None,
        approved_panel_ids: List[str] | None = None,
    ) -> StoryboardDecisionResult:
        approval = self.approvals.get_scoped(approval_id, actor.org_id, for_update=True)
        if approval.status != ApprovalStatus.PENDING.value:
            raise InvalidStateError(f"Approval request already {approval.status}.")
        project = self.projects.get_scoped(approval.project_id, actor.org_id)
        self.authz.require(actor, "approval.creative", project)

        record_decision(approval, decision, actor.user_id, notes)
        self.audit.record(
            project_id=approval.project_id,
            organization_id=approval.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.APPROVAL_DECIDED,
            target_type="approval_request",
            target_id=approval.id,
            details={"decision": decision.value, "notes": notes},
        )
        self.db.commit()

        review = StoryboardReviewService(self.db)
        if decision == ApprovalDecision.APPROVED:
            new_version = review.commit_approved_candidates(approval.workflow_run_id, notes, actor.user_id, approved_panel_ids)
        else:
            review.reject_candidates(approval.workflow_run_id, notes, actor.user_id)
            new_version = self.projects.get_scoped(approval.project_id, actor.org_id).current_version

        run = self.runs.get(approval.workflow_run_id)
        return StoryboardDecisionResult(
            approval_id=approval_id,
            decision=decision.value,
            run_status=run.status,
            new_project_version=new_version,
        )
