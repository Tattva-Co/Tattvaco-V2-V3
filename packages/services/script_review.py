"""Canonical-state operations for the Script Intelligence review cycle.

LangGraph nodes orchestrate; these methods own every write to canonical tables
(ADR-001 invariant 2). Each public method is one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List, Sequence

from sqlalchemy.orm import Session

from packages.domain.enums import (
    SCRIPT_INTELLIGENCE_APPROVAL_SCOPE,
    ApprovalDecision,
    ApprovalStatus,
    AuditAction,
    CandidateStatus,
    WorkflowStatus,
)
from packages.domain.errors import ValidationFailure
from packages.domain.invariants import assert_expected_version
from packages.persistence.models import (
    ApprovalRequestModel,
    EntityCandidateModel,
    EntityModel,
    ProjectVersionModel,
    SceneCandidateModel,
    SceneModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AssetRepository,
    AuditRepository,
    CandidateRepository,
    CanonicalRepository,
    ProjectRepository,
    WorkflowRunRepository,
)
from packages.storage.service import StorageService

SUPPORTED_SCRIPT_MIME_PREFIX = "text/"


@dataclass(frozen=True)
class RunScope:
    """Identifies one workflow run and the tenant/project it belongs to."""

    run_id: str
    project_id: str
    org_id: str


@dataclass
class ProposedCandidates:
    approval_request_id: str
    scenes: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]


def record_decision(
    approval: ApprovalRequestModel, decision: ApprovalDecision, actor_id: str, notes: str | None
) -> None:
    approval.status = ApprovalStatus.DECIDED.value
    approval.decision = decision.value
    approval.decision_notes = notes
    approval.decided_by = actor_id
    approval.decided_at = datetime.now(UTC)


class ScriptReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.candidates = CandidateRepository(db)
        self.approvals = ApprovalRepository(db)
        self.runs = WorkflowRunRepository(db)
        self.audit = AuditRepository(db)

    # -- input ---------------------------------------------------------------

    def load_script_text(self, asset_id: str, storage: StorageService) -> str:
        asset = AssetRepository(self.db).get(asset_id)
        if asset is None:
            raise ValidationFailure(f"Script asset '{asset_id}' no longer exists.")
        if not asset.mime_type.startswith(SUPPORTED_SCRIPT_MIME_PREFIX):
            raise ValidationFailure(
                f"Script Intelligence supports plain-text/Fountain scripts; got '{asset.mime_type}'."
            )
        return storage.get_bytes(asset.storage_path).decode("utf-8", errors="replace")

    # -- propose -------------------------------------------------------------

    def propose(
        self,
        scope: RunScope,
        actor_id: str,
        scenes: Sequence[Dict[str, Any]],
        entities: Sequence[Dict[str, Any]],
    ) -> ProposedCandidates:
        scene_rows = [
            self.candidates.add_scene(
                SceneCandidateModel(
                    workflow_run_id=scope.run_id,
                    project_id=scope.project_id,
                    scene_number=s["scene_number"],
                    heading=s["heading"],
                    setting=s["setting"],
                    location_name=s["location_name"],
                    time_of_day=s["time_of_day"],
                    summary=s["summary"],
                    source_locator=s["source_locator"],
                    characters_present=s["characters_present"],
                    status=CandidateStatus.PROPOSED.value,
                )
            )
            for s in scenes
        ]
        entity_rows = [
            self.candidates.add_entity(
                EntityCandidateModel(
                    workflow_run_id=scope.run_id,
                    project_id=scope.project_id,
                    name=e["name"],
                    category=e["category"],
                    description=e["description"],
                    source_locator=e["source_locator"],
                    confidence=e.get("confidence", 0.9),
                    status=CandidateStatus.PROPOSED.value,
                )
            )
            for e in entities
        ]

        scene_summaries = [
            {"id": r.id, "scene_number": r.scene_number, "heading": r.heading, "summary": r.summary}
            for r in scene_rows
        ]
        entity_summaries = [
            {"id": r.id, "name": r.name, "category": r.category, "confidence": r.confidence}
            for r in entity_rows
        ]
        approval = self.approvals.add(
            ApprovalRequestModel(
                workflow_run_id=scope.run_id,
                project_id=scope.project_id,
                organization_id=scope.org_id,
                scope=SCRIPT_INTELLIGENCE_APPROVAL_SCOPE,
                candidate_summary={
                    "scene_count": len(scene_rows),
                    "entity_count": len(entity_rows),
                    "scenes": scene_summaries,
                    "entities": entity_summaries,
                },
                status=ApprovalStatus.PENDING.value,
            )
        )
        self.audit.record(
            project_id=scope.project_id,
            organization_id=scope.org_id,
            actor_id=actor_id,
            action=AuditAction.CANDIDATES_EXTRACTED,
            target_type="approval_request",
            target_id=approval.id,
            details={
                "workflow_run_id": scope.run_id,
                "scenes_proposed": len(scene_rows),
                "entities_proposed": len(entity_rows),
            },
        )
        self.runs.set_status(scope.run_id, WorkflowStatus.AWAITING_APPROVAL.value)
        self.db.commit()

        return ProposedCandidates(
            approval_request_id=approval.id,
            scenes=[{**s, "candidate_id": r.id} for s, r in zip(scenes, scene_rows)],
            entities=[{**e, "candidate_id": r.id} for e, r in zip(entities, entity_rows)],
        )

    # -- decide --------------------------------------------------------------

    def _ensure_decision_recorded(
        self, scope: RunScope, decision: ApprovalDecision, actor_id: str, notes: str | None
    ) -> None:
        """The API records decisions before resuming (invariant 4). This covers direct resumes."""
        approval = self.approvals.get_pending_for_run(scope.run_id)
        if approval is not None:
            record_decision(approval, decision, actor_id, notes)

    def promote_approved(
        self,
        scope: RunScope,
        actor_id: str,
        expected_version: int,
        approved_scene_ids: Sequence[str] | None,
        approved_entity_ids: Sequence[str] | None,
        notes: str | None = None,
    ) -> int:
        """Promote selected candidates to canonical state and advance the project version.

        ``None`` for an id list means "all candidates"; an empty list means "none".
        Returns the new project version.
        """
        projects = ProjectRepository(self.db)
        project = projects.get_scoped(scope.project_id, scope.org_id, for_update=True)
        assert_expected_version(project.current_version, expected_version)
        next_version = project.current_version + 1

        def selected(candidate_id: str, chosen: Sequence[str] | None) -> bool:
            return chosen is None or candidate_id in set(chosen)

        promoted_scenes: List[SceneModel] = []
        for sc in self.candidates.scenes_for_run(scope.run_id):
            if selected(sc.id, approved_scene_ids):
                sc.status = CandidateStatus.APPROVED.value
                promoted_scenes.append(
                    SceneModel(
                        project_id=scope.project_id,
                        scene_number=sc.scene_number,
                        heading=sc.heading,
                        setting=sc.setting,
                        location_name=sc.location_name,
                        time_of_day=sc.time_of_day,
                        summary=sc.summary,
                        source_locator=sc.source_locator,
                        characters_present=sc.characters_present,
                        project_version=next_version,
                    )
                )
            else:
                sc.status = CandidateStatus.REJECTED.value

        promoted_entities: List[EntityModel] = []
        for ec in self.candidates.entities_for_run(scope.run_id):
            if selected(ec.id, approved_entity_ids):
                ec.status = CandidateStatus.APPROVED.value
                promoted_entities.append(
                    EntityModel(
                        project_id=scope.project_id,
                        name=ec.name,
                        category=ec.category,
                        description=ec.description,
                        source_locator=ec.source_locator,
                        project_version=next_version,
                    )
                )
            else:
                ec.status = CandidateStatus.REJECTED.value

        canonical = CanonicalRepository(self.db)
        canonical.add_scenes(promoted_scenes)
        canonical.add_entities(promoted_entities)

        project.current_version = next_version
        version = projects.add_version(
            ProjectVersionModel(
                project_id=scope.project_id,
                version_number=next_version,
                branch_name="main",
                commit_message=(
                    f"Script Intelligence extraction: {len(promoted_scenes)} scenes, "
                    f"{len(promoted_entities)} entities"
                ),
                committed_by=actor_id,
                snapshot_data={
                    "scenes_count": len(promoted_scenes),
                    "entities_count": len(promoted_entities),
                    "workflow_run_id": scope.run_id,
                },
            )
        )
        self._ensure_decision_recorded(scope, ApprovalDecision.APPROVED, actor_id, notes)
        self.audit.record(
            project_id=scope.project_id,
            organization_id=scope.org_id,
            actor_id=actor_id,
            action=AuditAction.SCRIPT_INTELLIGENCE_COMMITTED,
            target_type="project_version",
            target_id=version.id,
            details={
                "previous_version": next_version - 1,
                "new_version": next_version,
                "promoted_scenes": len(promoted_scenes),
                "promoted_entities": len(promoted_entities),
            },
        )
        self.runs.set_status(
            scope.run_id,
            WorkflowStatus.COMPLETED.value,
            output_refs={
                "new_version": next_version,
                "scenes_count": len(promoted_scenes),
                "entities_count": len(promoted_entities),
            },
        )
        self.db.commit()
        return next_version

    def close_rejected(self, scope: RunScope, actor_id: str, notes: str | None = None) -> None:
        """Reject every candidate of the run; canonical project state is untouched."""
        for candidate in [*self.candidates.scenes_for_run(scope.run_id), *self.candidates.entities_for_run(scope.run_id)]:
            candidate.status = CandidateStatus.REJECTED.value
        self._ensure_decision_recorded(scope, ApprovalDecision.REJECTED, actor_id, notes)
        self.audit.record(
            project_id=scope.project_id,
            organization_id=scope.org_id,
            actor_id=actor_id,
            action=AuditAction.SCRIPT_INTELLIGENCE_REJECTED,
            target_type="workflow_run",
            target_id=scope.run_id,
            details={"notes": notes},
        )
        self.runs.set_status(scope.run_id, WorkflowStatus.REJECTED.value)
        self.db.commit()
