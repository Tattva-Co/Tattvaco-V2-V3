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
    AssetScanStatus,
    AuditAction,
    CandidateStatus,
    WorkflowStatus,
)
from packages.domain.errors import AssetNotReadyError, ValidationFailure
from packages.domain.invariants import assert_expected_version
from packages.persistence.models import (
    ApprovalRequestModel,
    CharacterModel,
    DialogueSegmentCandidateModel,
    DialogueSegmentModel,
    EntityCandidateModel,
    EntityModel,
    LocationModel,
    ProjectVersionModel,
    SceneCandidateModel,
    SceneModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AssetDerivativeRepository,
    AssetRepository,
    AuditRepository,
    CandidateRepository,
    CanonicalRepository,
    CharacterRepository,
    LocationRepository,
    ProjectRepository,
    WorkflowRunRepository,
)
from packages.services.assets import DERIVATIVE_TYPE_EXTRACTED_TEXT
from packages.services.extraction import EXTRACTABLE_MIME_TYPES
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
    dialogue_segments: List[Dict[str, Any]]


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
        self.characters = CharacterRepository(db)
        self.locations = LocationRepository(db)
        self.audit = AuditRepository(db)

    # -- input ---------------------------------------------------------------

    def load_script_text(self, asset_id: str, storage: StorageService) -> str:
        asset = AssetRepository(self.db).get(asset_id)
        if asset is None:
            raise ValidationFailure(f"Script asset '{asset_id}' no longer exists.")
        if asset.scan_status != AssetScanStatus.CLEAN.value:
            raise AssetNotReadyError(
                f"Script asset '{asset_id}' is not usable yet (scan_status={asset.scan_status!r})."
            )
        if asset.mime_type.startswith(SUPPORTED_SCRIPT_MIME_PREFIX):
            return storage.get_bytes(asset.storage_path).decode("utf-8", errors="replace")
        if asset.mime_type in EXTRACTABLE_MIME_TYPES:
            derivative = AssetDerivativeRepository(self.db).get_for_asset(asset.id, DERIVATIVE_TYPE_EXTRACTED_TEXT)
            if derivative is None or derivative.extraction_error:
                detail = derivative.extraction_error if derivative else "no extraction was recorded for this asset"
                raise ValidationFailure(
                    f"Could not extract text from '{asset.filename}' ({asset.mime_type}): {detail}"
                )
            return derivative.content
        raise ValidationFailure(
            f"Script Intelligence supports plain-text/Fountain, PDF, DOCX and Final Draft "
            f"(.fdx) scripts; got '{asset.mime_type}'."
        )

    # -- propose -------------------------------------------------------------

    def propose(
        self,
        scope: RunScope,
        actor_id: str,
        scenes: Sequence[Dict[str, Any]],
        entities: Sequence[Dict[str, Any]],
        dialogue_segments: Sequence[Dict[str, Any]] = (),
    ) -> ProposedCandidates:
        run = self.runs.get(scope.run_id)
        scene_rows = [
            self.candidates.add_scene(
                SceneCandidateModel(
                    workflow_run_id=scope.run_id,
                    project_id=scope.project_id,
                    organization_id=scope.org_id,
                    scene_number=s["scene_number"],
                    heading=s["heading"],
                    setting=s["setting"],
                    location_name=s["location_name"],
                    time_of_day=s["time_of_day"],
                    summary=s["summary"],
                    source_locator=s["source_locator"],
                    characters_present=s["characters_present"],
                    status=CandidateStatus.PROPOSED.value,
                    generator_mode=run.generator_mode,
                )
            )
            for s in scenes
        ]
        entity_rows = [
            self.candidates.add_entity(
                EntityCandidateModel(
                    workflow_run_id=scope.run_id,
                    project_id=scope.project_id,
                    organization_id=scope.org_id,
                    name=e["name"],
                    category=e["category"],
                    description=e["description"],
                    source_locator=e["source_locator"],
                    confidence=e.get("confidence", 0.9),
                    status=CandidateStatus.PROPOSED.value,
                    generator_mode=run.generator_mode,
                    aliases=e.get("aliases", []),
                )
            )
            for e in entities
        ]
        dialogue_rows = [
            self.candidates.add_dialogue_segment(
                DialogueSegmentCandidateModel(
                    workflow_run_id=scope.run_id,
                    project_id=scope.project_id,
                    organization_id=scope.org_id,
                    scene_number=d["scene_number"],
                    character_name=d["character_name"],
                    line_text=d["line_text"],
                    parenthetical=d.get("parenthetical"),
                    order_in_scene=d["order_in_scene"],
                    source_locator=d["source_locator"],
                    status=CandidateStatus.PROPOSED.value,
                    generator_mode=run.generator_mode,
                )
            )
            for d in dialogue_segments
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
                    "dialogue_segment_count": len(dialogue_rows),
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
                "dialogue_segments_proposed": len(dialogue_rows),
            },
        )
        self.runs.set_status(scope.run_id, WorkflowStatus.AWAITING_APPROVAL.value)
        self.db.commit()

        return ProposedCandidates(
            approval_request_id=approval.id,
            scenes=[{**s, "candidate_id": r.id} for s, r in zip(scenes, scene_rows)],
            entities=[{**e, "candidate_id": r.id} for e, r in zip(entities, entity_rows)],
            dialogue_segments=[{**d, "candidate_id": r.id} for d, r in zip(dialogue_segments, dialogue_rows)],
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
        # D2 (TFD-SCR-009): stamp every newly-promoted scene with the screenplay
        # version Script Intelligence actually read from -- off the run row, the same
        # "metadata lives on the run" pattern C10's generator_mode established.
        run = self.runs.get(scope.run_id)
        screenplay_version_id = run.screenplay_version_id if run else None

        def selected(candidate_id: str, chosen: Sequence[str] | None) -> bool:
            return chosen is None or candidate_id in set(chosen)

        promoted_scenes: List[SceneModel] = []
        approved_scene_numbers: set[int] = set()
        for sc in self.candidates.scenes_for_run(scope.run_id):
            if selected(sc.id, approved_scene_ids):
                sc.status = CandidateStatus.APPROVED.value
                approved_scene_numbers.add(sc.scene_number)
                promoted_scenes.append(
                    SceneModel(
                        project_id=scope.project_id,
                        organization_id=scope.org_id,
                        scene_number=sc.scene_number,
                        heading=sc.heading,
                        setting=sc.setting,
                        location_name=sc.location_name,
                        time_of_day=sc.time_of_day,
                        summary=sc.summary,
                        source_locator=sc.source_locator,
                        characters_present=sc.characters_present,
                        project_version=next_version,
                        screenplay_version_id=screenplay_version_id,
                    )
                )
            else:
                sc.status = CandidateStatus.REJECTED.value

        promoted_entities: List[EntityModel] = []
        for ec in self.candidates.entities_for_run(scope.run_id):
            if selected(ec.id, approved_entity_ids):
                ec.status = CandidateStatus.APPROVED.value
                entity = EntityModel(
                    project_id=scope.project_id,
                    organization_id=scope.org_id,
                    name=ec.name,
                    category=ec.category,
                    description=ec.description,
                    source_locator=ec.source_locator,
                    project_version=next_version,
                    aliases=ec.aliases,
                )
                # D3 (TFD-STY-003): resolve into the project's one character/location
                # row for this name -- reusing it across runs, not duplicating one per
                # run the way entities themselves accumulate.
                if ec.category == "character":
                    entity.resolved_character_id = self._resolve_character(
                        scope, ec.name, ec.aliases, next_version
                    )
                elif ec.category == "location":
                    entity.resolved_location_id = self._resolve_location(
                        scope, ec.name, ec.aliases, next_version
                    )
                promoted_entities.append(entity)
            else:
                ec.status = CandidateStatus.REJECTED.value

        canonical = CanonicalRepository(self.db)
        canonical.add_scenes(promoted_scenes)
        canonical.add_entities(promoted_entities)
        self.db.flush()  # assign scene ids before dialogue segments reference them

        scene_id_by_number = {sc.scene_number: sc.id for sc in promoted_scenes}
        promoted_dialogue_segments: List[DialogueSegmentModel] = []
        for dc in self.candidates.dialogue_segments_for_run(scope.run_id):
            # Dialogue has no approval checkbox of its own (TFD-STY-002: verbatim, not
            # independently editable) -- it is promoted exactly when its own scene is.
            if dc.scene_number in approved_scene_numbers:
                dc.status = CandidateStatus.APPROVED.value
                character = self.characters.get_by_name(scope.project_id, dc.character_name)
                promoted_dialogue_segments.append(
                    DialogueSegmentModel(
                        project_id=scope.project_id,
                        organization_id=scope.org_id,
                        scene_id=scene_id_by_number[dc.scene_number],
                        screenplay_version_id=screenplay_version_id,
                        character_id=character.id if character else None,
                        character_name=dc.character_name,
                        line_text=dc.line_text,
                        parenthetical=dc.parenthetical,
                        order_in_scene=dc.order_in_scene,
                        source_locator=dc.source_locator,
                        project_version=next_version,
                    )
                )
            else:
                dc.status = CandidateStatus.REJECTED.value
        canonical.add_dialogue_segments(promoted_dialogue_segments)

        project.current_version = next_version
        version = projects.add_version(
            ProjectVersionModel(
                project_id=scope.project_id,
                organization_id=scope.org_id,
                version_number=next_version,
                branch_name="main",
                commit_message=(
                    f"Script Intelligence extraction: {len(promoted_scenes)} scenes, "
                    f"{len(promoted_entities)} entities, {len(promoted_dialogue_segments)} dialogue segments"
                ),
                committed_by=actor_id,
                snapshot_data={
                    "scenes_count": len(promoted_scenes),
                    "entities_count": len(promoted_entities),
                    "dialogue_segments_count": len(promoted_dialogue_segments),
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
                "promoted_dialogue_segments": len(promoted_dialogue_segments),
            },
        )
        self.runs.set_status(
            scope.run_id,
            WorkflowStatus.COMPLETED.value,
            output_refs={
                "new_version": next_version,
                "scenes_count": len(promoted_scenes),
                "entities_count": len(promoted_entities),
                "dialogue_segments_count": len(promoted_dialogue_segments),
            },
        )
        self.db.commit()
        return next_version

    def _resolve_character(
        self, scope: RunScope, name: str, aliases: List[str], project_version: int
    ) -> str:
        """TFD-STY-003: one `characters` row per distinct identity per project, reused
        (and its aliases grown) across every run that mentions them again, rather than
        one new row per run the way `entities` itself accumulates."""
        existing = self.characters.get_by_name(scope.project_id, name)
        if existing is not None:
            for alias in aliases:
                if alias not in existing.aliases:
                    existing.aliases = [*existing.aliases, alias]
            return existing.id
        character = self.characters.add(
            CharacterModel(
                project_id=scope.project_id,
                organization_id=scope.org_id,
                canonical_name=name,
                aliases=list(aliases),
                project_version=project_version,
            )
        )
        return character.id

    def _resolve_location(
        self, scope: RunScope, name: str, aliases: List[str], project_version: int
    ) -> str:
        existing = self.locations.get_by_name(scope.project_id, name)
        if existing is not None:
            for alias in aliases:
                if alias not in existing.aliases:
                    existing.aliases = [*existing.aliases, alias]
            return existing.id
        location = self.locations.add(
            LocationModel(
                project_id=scope.project_id,
                organization_id=scope.org_id,
                canonical_name=name,
                aliases=list(aliases),
                project_version=project_version,
            )
        )
        return location.id

    def close_rejected(self, scope: RunScope, actor_id: str, notes: str | None = None) -> None:
        """Reject every candidate of the run; canonical project state is untouched."""
        for candidate in [
            *self.candidates.scenes_for_run(scope.run_id),
            *self.candidates.entities_for_run(scope.run_id),
            *self.candidates.dialogue_segments_for_run(scope.run_id),
        ]:
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
