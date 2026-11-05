"""Canonical-state operations for Storyboard Intelligence review cycle.

LangGraph nodes orchestrate; these methods own every write to canonical tables
(ADR-001 invariant 2). Each public method is one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy.orm import Session

from packages.domain.enums import (
    STORYBOARD_INTELLIGENCE_APPROVAL_SCOPE,
    ApprovalStatus,
    AuditAction,
    CandidateStatus,
    WorkflowStatus,
)
from packages.domain.errors import ValidationFailure
from packages.domain.invariants import assert_expected_version
from packages.persistence.models import (
    ApprovalRequestModel,
    ProjectVersionModel,
    StoryboardPanelCandidateModel,
    StoryboardPanelModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CandidateRepository,
    CanonicalRepository,
    ProjectRepository,
    StoryboardRepository,
    WorkflowRunRepository,
)


@dataclass(frozen=True)
class RunScope:
    run_id: str
    project_id: str
    org_id: str


@dataclass
class ProposedStoryboardCandidates:
    approval_request_id: str
    panels: list[dict[str, Any]]


class StoryboardReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.runs = WorkflowRunRepository(db)
        self.approvals = ApprovalRepository(db)
        self.candidates = CandidateRepository(db)
        self.storyboard = StoryboardRepository(db)
        self.canonical = CanonicalRepository(db)
        self.audit = AuditRepository(db)

    def validate_scope(self, run_id: str) -> RunScope:
        run = self.runs.get(run_id)
        project = self.projects.get_scoped(run.project_id, run.organization_id)
        assert_expected_version(project.current_version, run.expected_project_version)
        return RunScope(run_id=run.id, project_id=project.id, org_id=project.organization_id)

    def propose_candidates(
        self,
        run_id: str,
        panels: Sequence[dict[str, Any]],
        actor_id: str | None = None,
    ) -> ProposedStoryboardCandidates:
        if not panels:
            raise ValidationFailure("No storyboard panels generated")

        scope = self.validate_scope(run_id)
        project = self.projects.get_scoped(scope.project_id, scope.org_id)
        effective_actor = actor_id or project.created_by

        panel_rows: list[StoryboardPanelCandidateModel] = []
        for p in panels:
            row = StoryboardPanelCandidateModel(
                workflow_run_id=scope.run_id,
                project_id=scope.project_id,
                organization_id=scope.org_id,
                panel_number=p["panel_number"],
                suggested_scene_number=p.get("suggested_scene_number"),
                shot_type=p.get("shot_type", "wide"),
                description=p["description"],
                visual_notes=p.get("visual_notes"),
                dialogue_snippet=p.get("dialogue_snippet"),
                confidence=float(p.get("confidence", 0.9)),
                status=CandidateStatus.PROPOSED.value,
            )
            self.candidates.add_storyboard_panel(row)
            panel_rows.append(row)

        approval = self.approvals.add(
            ApprovalRequestModel(
                workflow_run_id=scope.run_id,
                organization_id=scope.org_id,
                project_id=scope.project_id,
                scope=STORYBOARD_INTELLIGENCE_APPROVAL_SCOPE,
                candidate_summary={
                    "panel_count": len(panel_rows),
                    "panels": [
                        {"id": r.id, "panel_number": r.panel_number, "shot_type": r.shot_type, "desc": r.description}
                        for r in panel_rows
                    ],
                },
                status=ApprovalStatus.PENDING.value,
            )
        )
        self.runs.set_status(scope.run_id, WorkflowStatus.AWAITING_APPROVAL.value)

        self.audit.record(
            project_id=scope.project_id,
            organization_id=scope.org_id,
            actor_id=effective_actor,
            action=AuditAction.CANDIDATES_EXTRACTED,
            target_type="approval_request",
            target_id=approval.id,
            details={
                "panel_count": len(panel_rows),
                "scope": STORYBOARD_INTELLIGENCE_APPROVAL_SCOPE,
            },
        )
        self.db.commit()

        return ProposedStoryboardCandidates(
            approval_request_id=approval.id,
            panels=[{**p, "candidate_id": r.id} for p, r in zip(panels, panel_rows, strict=False)],
        )

    def commit_approved_candidates(
        self,
        run_id: str,
        decision_notes: str | None,
        decided_by: str | None,
        approved_panel_ids: Sequence[str] | None = None,
    ) -> int:
        scope = self.validate_scope(run_id)
        # Lock the project row so concurrent approvals cannot produce duplicate versions
        # (docs/audit/08 PERF-06). validate_scope's own read happened before this lock was
        # acquired, so the version is re-checked once the lock is held.
        project = self.projects.get_scoped(scope.project_id, scope.org_id, for_update=True)
        assert_expected_version(project.current_version, self.runs.get(run_id).expected_project_version)
        panel_rows = self.candidates.storyboard_panels_for_run(run_id)

        target_panel_ids = set(approved_panel_ids) if approved_panel_ids is not None else {p.id for p in panel_rows}

        new_version = project.current_version + 1
        actor_id = decided_by or project.created_by

        # Map canonical scenes by scene_number for linking
        scenes = self.canonical.scenes_for_project(scope.project_id)
        scenes_by_num = {s.scene_number: s.id for s in scenes}

        committed_count = 0
        for p in panel_rows:
            if p.id in target_panel_ids:
                p.status = CandidateStatus.APPROVED.value
                linked_scene_id = scenes_by_num.get(p.suggested_scene_number)
                model = StoryboardPanelModel(
                    project_id=scope.project_id,
                    organization_id=scope.org_id,
                    project_version=new_version,
                    panel_number=p.panel_number,
                    scene_id=linked_scene_id,
                    shot_type=p.shot_type,
                    description=p.description,
                    visual_notes=p.visual_notes,
                    dialogue_snippet=p.dialogue_snippet,
                    aspect_ratio="16:9",
                )
                self.storyboard.add_panel(model)
                committed_count += 1
            else:
                p.status = CandidateStatus.REJECTED.value

        project.current_version = new_version
        version_row = ProjectVersionModel(
            project_id=project.id,
            version_number=new_version,
            branch_name="main",
            commit_message=f"Storyboard Intelligence committed: {committed_count} panels",
            committed_by=actor_id,
            snapshot_data={
                "panels_committed": committed_count,
                "notes": decision_notes,
            },
        )
        self.db.add(version_row)

        run = self.runs.get(run_id)
        run.status = WorkflowStatus.COMPLETED.value
        self.db.flush()

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor_id,
            action=AuditAction.STORYBOARD_COMMITTED,
            target_type="project_version",
            target_id=version_row.id,
            details={
                "new_version": new_version,
                "panels_committed": committed_count,
                "workflow_run_id": run_id,
            },
        )
        self.db.commit()
        return new_version

    def reject_candidates(self, run_id: str, notes: str | None, actor_id: str | None) -> int:
        scope = self.validate_scope(run_id)
        project = self.projects.get_scoped(scope.project_id, scope.org_id)

        for p in self.candidates.storyboard_panels_for_run(run_id):
            p.status = CandidateStatus.REJECTED.value

        run = self.runs.get(run_id)
        run.status = WorkflowStatus.REJECTED.value

        actor = actor_id or project.created_by
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor,
            action=AuditAction.STORYBOARD_REJECTED,
            target_type="workflow_run",
            target_id=run.id,
            details={"notes": notes, "status": "rejected"},
        )
        self.db.commit()
        return project.current_version

