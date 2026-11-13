"""Screenplay governance (D2, PRD §3): import, director-led revisions, suggestions,
management lock/approval, and impact analysis.

Not a LangGraph workflow -- unlike WF-01..04, there is no AI-authored candidate content
to generate-then-approve here; this is a plain state machine (PRD §3.1) plus human
review, so a direct service (same shape as ``ProjectService``) is the right tool, not a
graph with an interrupt.
"""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.ai.gateway import get_model_gateway
from packages.core.config import get_settings
from packages.domain.enums import (
    REVIEW_STATUS_REQUIRED,
    ApprovalDecision,
    ApprovalStatus,
    AuditAction,
    ScreenplayVersionStatus,
)
from packages.domain.errors import InvalidStateError, NotFoundError, ValidationFailure
from packages.persistence.models import (
    ApprovalRequestModel,
    ImpactAnalysisModel,
    ScreenplayChangeModel,
    ScreenplaySuggestionModel,
    ScreenplayVersionModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AssetRepository,
    AuditRepository,
    CanonicalRepository,
    ProjectRepository,
    ScreenplayRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext
from packages.services.script_review import ScriptReviewService, record_decision
from packages.storage.factory import get_storage
from packages.workflows.script_intelligence.parser import ScreenplayParser

#: Scope on ApprovalRequestModel rows for a screenplay revision's management decision
#: (C8's generalized target_type/target_id, used for the first time here).
SCREENPLAY_LOCK_APPROVAL_SCOPE = "screenplay_lock"
SCREENPLAY_VERSION_TARGET_TYPE = "screenplay_version"


def _content_hash(content_text: str) -> str:
    return hashlib.sha256(content_text.encode("utf-8")).hexdigest()


def _compute_diff(before_text: str, after_text: str) -> Dict[str, Any]:
    """Line-level unified diff (covers dialogue-level changes) plus a scene-level
    summary (AT-SCR-006.1: "the diff lists the scene-level and dialogue-level changes"),
    reusing the same parser every other screenplay-reading code path uses."""
    before_lines = before_text.splitlines()
    after_lines = after_text.splitlines()
    unified = "\n".join(difflib.unified_diff(before_lines, after_lines, lineterm=""))

    before_scenes, _, _ = ScreenplayParser().parse(before_text)
    after_scenes, _, _ = ScreenplayParser().parse(after_text)
    before_by_number = {s["scene_number"]: s for s in before_scenes}
    after_by_number = {s["scene_number"]: s for s in after_scenes}

    scenes_changed: List[Dict[str, Any]] = []
    for number in sorted(set(before_by_number) | set(after_by_number)):
        before_scene, after_scene = before_by_number.get(number), after_by_number.get(number)
        if before_scene is None:
            scenes_changed.append({"scene_number": number, "change": "added"})
        elif after_scene is None:
            scenes_changed.append({"scene_number": number, "change": "removed"})
        elif before_scene["heading"] != after_scene["heading"] or before_scene["summary"] != after_scene["summary"]:
            scenes_changed.append({"scene_number": number, "change": "modified"})

    return {
        "unified_diff": unified,
        "scenes_changed": scenes_changed,
        "lines_added": sum(1 for line in unified.splitlines() if line.startswith("+") and not line.startswith("+++")),
        "lines_removed": sum(1 for line in unified.splitlines() if line.startswith("-") and not line.startswith("---")),
    }


@dataclass
class RevisionDecisionResult:
    approval_id: str
    decision: str
    version_status: str
    is_canonical: bool


class ScreenplayGovernanceService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.screenplay = ScreenplayRepository(db)
        self.canonical = CanonicalRepository(db)
        self.approvals = ApprovalRepository(db)
        self.audit = AuditRepository(db)
        self.authz = AuthzService(db)

    # -- import & revisions ---------------------------------------------------

    def import_version(
        self, actor: ActorContext, project_id: str, source_asset_id: str, *, episode_id: str | None = None
    ) -> ScreenplayVersionModel:
        """TFD-SCR-001: a fresh root-level draft, not derived from any other version."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "screenplay.propose_revision", project)
        asset = AssetRepository(self.db).get_for_project(source_asset_id, project_id)
        content_text = ScriptReviewService(self.db).load_script_text(asset.id, get_storage())

        version = self.screenplay.add_version(
            ScreenplayVersionModel(
                project_id=project.id,
                organization_id=project.organization_id,
                episode_id=episode_id,
                version_number=self.screenplay.next_version_number(project_id, episode_id),
                status=ScreenplayVersionStatus.DRAFT.value,
                is_production_canonical=False,
                source_asset_id=asset.id,
                derived_from_version_id=None,
                content_text=content_text,
                content_hash=_content_hash(content_text),
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.SCREENPLAY_VERSION_IMPORTED,
            target_type="screenplay_version",
            target_id=version.id,
            details={"source_asset_id": asset.id, "version_number": version.version_number},
        )
        self.db.commit()
        self.db.refresh(version)
        return version

    def create_revision(self, actor: ActorContext, project_id: str, base_version_id: str) -> ScreenplayVersionModel:
        """TFD-SCR-006: a new draft derived from any existing version (typically the
        canonical one), its content_text a starting copy the Director then edits."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "screenplay.propose_revision", project)
        base = self.screenplay.get_version_scoped(base_version_id, project_id)

        revision = self.screenplay.add_version(
            ScreenplayVersionModel(
                project_id=project.id,
                organization_id=project.organization_id,
                episode_id=base.episode_id,
                version_number=self.screenplay.next_version_number(project_id, base.episode_id),
                status=ScreenplayVersionStatus.DRAFT.value,
                is_production_canonical=False,
                source_asset_id=None,
                derived_from_version_id=base.id,
                content_text=base.content_text,
                content_hash=base.content_hash,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.SCREENPLAY_REVISION_CREATED,
            target_type="screenplay_version",
            target_id=revision.id,
            details={"derived_from_version_id": base.id, "version_number": revision.version_number},
        )
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def update_content(self, actor: ActorContext, project_id: str, version_id: str, content_text: str) -> ScreenplayVersionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "screenplay.propose_revision", project)
        version = self.screenplay.get_version_scoped(version_id, project_id)
        self._assert_mutable(version, actor)

        version.content_text = content_text
        version.content_hash = _content_hash(content_text)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.SCREENPLAY_REVISION_EDITED,
            target_type="screenplay_version",
            target_id=version.id,
            details={},
        )
        self.db.commit()
        self.db.refresh(version)
        return version

    def list_versions(self, actor: ActorContext, project_id: str) -> List[ScreenplayVersionModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.screenplay.list_versions_for_project(project_id)

    def get_version(self, actor: ActorContext, project_id: str, version_id: str) -> ScreenplayVersionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.screenplay.get_version_scoped(version_id, project_id)

    def diff(self, actor: ActorContext, project_id: str, version_id: str, against_version_id: str) -> Dict[str, Any]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        version = self.screenplay.get_version_scoped(version_id, project_id)
        against = self.screenplay.get_version_scoped(against_version_id, project_id)
        return _compute_diff(against.content_text, version.content_text)

    # -- submit & decide --------------------------------------------------------

    def submit_for_review(
        self, actor: ActorContext, project_id: str, version_id: str, justification: str | None
    ) -> ScreenplayVersionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "screenplay.propose_revision", project)
        version = self.screenplay.get_version_scoped(version_id, project_id)
        self._assert_mutable(version, actor)

        # AT-SCR-006.2: a change set without justification is rejected, status stays draft.
        if not justification or not justification.strip():
            raise ValidationFailure("A justification is required to submit a screenplay revision for review.")

        base = None
        if version.derived_from_version_id:
            base = self.screenplay.get_version_scoped(version.derived_from_version_id, project_id)
        else:
            base = self.screenplay.get_canonical(project_id, version.episode_id)
        diff_summary = _compute_diff(base.content_text, version.content_text) if base else {
            "unified_diff": "", "scenes_changed": [], "lines_added": 0, "lines_removed": 0
        }

        self.screenplay.add_change(
            ScreenplayChangeModel(
                screenplay_version_id=version.id,
                project_id=project.id,
                organization_id=project.organization_id,
                diffed_against_version_id=base.id if base else version.id,
                diff_summary=diff_summary,
                justification=justification.strip(),
                submitted_by=actor.user_id,
            )
        )
        version.status = ScreenplayVersionStatus.IN_REVIEW.value
        version.submitted_at = datetime.now(UTC)
        version.submitted_by = actor.user_id

        self.approvals.add(
            ApprovalRequestModel(
                workflow_run_id=None,
                target_type=SCREENPLAY_VERSION_TARGET_TYPE,
                target_id=version.id,
                project_id=project.id,
                organization_id=project.organization_id,
                scope=SCREENPLAY_LOCK_APPROVAL_SCOPE,
                candidate_summary=diff_summary,
                status=ApprovalStatus.PENDING.value,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.SCREENPLAY_REVISION_SUBMITTED,
            target_type="screenplay_version",
            target_id=version.id,
            details={"justification": justification.strip()},
        )
        self.db.commit()
        self.db.refresh(version)
        return version

    def decide_revision(
        self,
        actor: ActorContext,
        project_id: str,
        version_id: str,
        decision: ApprovalDecision,
        notes: str | None,
    ) -> RevisionDecisionResult:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "screenplay.approve_lock", project)
        version = self.screenplay.get_version_scoped(version_id, project_id)
        if version.status != ScreenplayVersionStatus.IN_REVIEW.value:
            raise InvalidStateError(f"Screenplay version '{version_id}' is not awaiting review.")

        approval = self.approvals.get_pending_for_target(SCREENPLAY_VERSION_TARGET_TYPE, version.id)
        if approval is None:
            raise NotFoundError(f"No pending approval for screenplay version '{version_id}'.")
        record_decision(approval, decision, actor.user_id, notes)

        if decision == ApprovalDecision.APPROVED:
            old_canonical = self.screenplay.get_canonical(project_id, version.episode_id)
            # Two flushes, deliberately in this order: the partial unique index
            # (project_id, episode_id) WHERE is_production_canonical checks immediately
            # per statement, not deferred (a partial index can't back a DEFERRABLE
            # constraint in Postgres) -- flushing "set the new version canonical" before
            # "unset the old one" would make a transaction conflict with *itself*
            # (both rows briefly true at once), even with no concurrent request at all.
            if old_canonical is not None:
                old_canonical.status = ScreenplayVersionStatus.SUPERSEDED.value
                old_canonical.is_production_canonical = False
                self.db.flush()
            version.status = ScreenplayVersionStatus.APPROVED_LOCKED.value
            version.is_production_canonical = True
            version.locked_at = datetime.now(UTC)
            version.locked_by = actor.user_id
            try:
                self.db.flush()  # AT-SCR-002.2: the unique partial index enforces this.
            except IntegrityError as exc:
                self.db.rollback()
                raise InvalidStateError(
                    "Another version was already approved as canonical for this project/episode."
                ) from exc
            self._record_impact_analysis(project, old_canonical, version, actor)
            action = AuditAction.SCREENPLAY_REVISION_APPROVED
        elif decision == ApprovalDecision.REJECTED:
            version.status = ScreenplayVersionStatus.REJECTED.value
            action = AuditAction.SCREENPLAY_REVISION_REJECTED
        elif decision == ApprovalDecision.CHANGES_REQUESTED:
            version.status = ScreenplayVersionStatus.DRAFT.value
            action = AuditAction.SCREENPLAY_REVISION_CHANGES_REQUESTED
        else:
            raise ValidationFailure(f"Unsupported decision for a screenplay revision: {decision!r}")

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=action,
            target_type="screenplay_version",
            target_id=version.id,
            details={"notes": notes},
        )
        self.db.commit()
        self.db.refresh(version)
        return RevisionDecisionResult(
            approval_id=approval.id,
            decision=decision.value,
            version_status=version.status,
            is_canonical=version.is_production_canonical,
        )

    def confirm_legacy_lock(self, actor: ActorContext, project_id: str, version_id: str) -> ScreenplayVersionModel:
        """PRD §3.1 "CURRENT" note: a backfilled v1 (imported before this feature
        existed) is promoted straight to the canonical lock by an explicit project-owner
        action, not auto-promoted by the migration that created it."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "screenplay.approve_lock", project)
        version = self.screenplay.get_version_scoped(version_id, project_id)
        if version.status != ScreenplayVersionStatus.DRAFT.value or version.derived_from_version_id is not None:
            raise InvalidStateError("Only a freshly imported draft version can be confirmed as the legacy lock.")
        if self.screenplay.get_canonical(project_id, version.episode_id) is not None:
            raise InvalidStateError("A canonical screenplay version already exists for this project.")

        version.status = ScreenplayVersionStatus.APPROVED_LOCKED.value
        version.is_production_canonical = True
        version.locked_at = datetime.now(UTC)
        version.locked_by = actor.user_id
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise InvalidStateError("A canonical screenplay version already exists for this project.") from exc

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.SCREENPLAY_LEGACY_LOCK_CONFIRMED,
            target_type="screenplay_version",
            target_id=version.id,
            details={},
        )
        self.db.commit()
        self.db.refresh(version)
        return version

    # -- impact analysis ---------------------------------------------------------

    def preview_impact(self, actor: ActorContext, project_id: str, version_id: str) -> Dict[str, Any]:
        """AT-SCR-010.2: the impact preview is visible to management before the
        decision. Read-only -- computes the same comparison _record_impact_analysis
        would, without writing an ImpactAnalysisModel row or flagging any canonical row."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "screenplay.approve_lock", project)
        version = self.screenplay.get_version_scoped(version_id, project_id)
        old_canonical = self.screenplay.get_canonical(project_id, version.episode_id)
        if old_canonical is None or old_canonical.id == version.id:
            return {"affected_items": []}
        return {"affected_items": self._affected_items(project_id, old_canonical, version)}

    def list_impact_analyses(self, actor: ActorContext, project_id: str) -> List[ImpactAnalysisModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.screenplay.list_impact_analyses_for_project(project_id)

    def _affected_items(
        self, project_id: str, old_canonical: ScreenplayVersionModel, new_version: ScreenplayVersionModel
    ) -> List[Dict[str, Any]]:
        diff = _compute_diff(old_canonical.content_text, new_version.content_text)
        changed_numbers = {c["scene_number"] for c in diff["scenes_changed"] if c["change"] in ("modified", "removed")}
        if not changed_numbers:
            return []

        affected: List[Dict[str, Any]] = []
        changed_character_names: set[str] = set()
        for scene in self.canonical.scenes_for_screenplay_version(old_canonical.id):
            if scene.scene_number in changed_numbers:
                affected.append({"item_type": "scene", "item_id": scene.id, "reason": "source screenplay text changed"})
                changed_character_names.update(scene.characters_present or [])

        if changed_character_names:
            for entity in self.canonical.entities_for_project(project_id):
                if entity.category == "character" and entity.name in changed_character_names:
                    affected.append(
                        {"item_type": "entity", "item_id": entity.id, "reason": "appeared only in a changed scene"}
                    )
        return affected

    def _record_impact_analysis(
        self,
        project,
        old_canonical: ScreenplayVersionModel | None,
        new_version: ScreenplayVersionModel,
        actor: ActorContext,
    ) -> ImpactAnalysisModel | None:
        if old_canonical is None:
            return None  # nothing to compare the very first lock against
        affected = self._affected_items(project.id, old_canonical, new_version)
        for item in affected:
            if item["item_type"] == "scene":
                scene = next((s for s in self.canonical.scenes_for_screenplay_version(old_canonical.id) if s.id == item["item_id"]), None)
                if scene is not None:
                    scene.review_status = REVIEW_STATUS_REQUIRED
            elif item["item_type"] == "entity":
                entity = next((e for e in self.canonical.entities_for_project(project.id) if e.id == item["item_id"]), None)
                if entity is not None:
                    entity.review_status = REVIEW_STATUS_REQUIRED

        analysis = self.screenplay.add_impact_analysis(
            ImpactAnalysisModel(
                project_id=project.id,
                organization_id=project.organization_id,
                trigger_type="screenplay_lock",
                new_version_id=new_version.id,
                previous_version_id=old_canonical.id,
                affected_items=affected,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.IMPACT_ANALYSIS_CREATED,
            target_type="impact_analysis",
            target_id=analysis.id,
            details={"affected_count": len(affected)},
        )
        return analysis

    # -- suggestions ---------------------------------------------------------

    def generate_suggestions(
        self, actor: ActorContext, project_id: str, version_id: str, scope_notes: str | None
    ) -> List[ScreenplaySuggestionModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "workflow.run", project)
        version = self.screenplay.get_version_scoped(version_id, project_id)

        gateway = get_model_gateway(get_settings())
        result = gateway.suggest_screenplay_revisions(version.content_text, scope_notes)
        rows = [
            self.screenplay.add_suggestion(
                ScreenplaySuggestionModel(
                    screenplay_version_id=version.id,
                    project_id=project.id,
                    organization_id=project.organization_id,
                    kind=s.kind,
                    anchor=s.anchor,
                    suggestion_text=s.suggestion_text,
                    rationale=s.rationale,
                    disposition="pending",
                    generator_mode=gateway.mode,
                )
            )
            for s in result.suggestions
        ]
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.SCREENPLAY_SUGGESTIONS_GENERATED,
            target_type="screenplay_version",
            target_id=version.id,
            details={"count": len(rows)},
        )
        self.db.commit()
        for row in rows:
            self.db.refresh(row)
        return rows

    def list_suggestions(self, actor: ActorContext, project_id: str, version_id: str) -> List[ScreenplaySuggestionModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.screenplay.list_suggestions_for_version(version_id)

    def decide_suggestion(
        self, actor: ActorContext, project_id: str, suggestion_id: str, disposition: str, notes: str | None
    ) -> ScreenplaySuggestionModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "approval.creative", project)
        suggestion = self.screenplay.get_suggestion_scoped(suggestion_id, project_id)
        if suggestion.disposition != "pending":
            raise InvalidStateError(f"Suggestion '{suggestion_id}' was already decided.")

        suggestion.disposition = disposition
        suggestion.disposition_notes = notes
        suggestion.decided_by = actor.user_id
        suggestion.decided_at = datetime.now(UTC)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.SCREENPLAY_SUGGESTION_DECIDED,
            target_type="screenplay_suggestion",
            target_id=suggestion.id,
            details={"disposition": disposition},
        )
        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    # -- internals ---------------------------------------------------------

    def _assert_mutable(self, version: ScreenplayVersionModel, actor: ActorContext) -> None:
        """TFD-SCR-003: any write path touching a non-draft version is rejected with
        409 `screenplay_locked`, audited (AT-SCR-003.1)."""
        if version.status != ScreenplayVersionStatus.DRAFT.value:
            self.audit.record(
                project_id=version.project_id,
                organization_id=version.organization_id,
                actor_id=actor.user_id,
                action=AuditAction.SCREENPLAY_LOCKED_MUTATION_BLOCKED,
                target_type="screenplay_version",
                target_id=version.id,
                details={"status": version.status},
            )
            self.db.commit()
            raise InvalidStateError(f"screenplay_locked: version is {version.status}, not draft.")
