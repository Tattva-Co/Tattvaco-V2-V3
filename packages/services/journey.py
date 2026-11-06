"""The Guided Workspace journey engine's service layer (GW1).

Orchestrates packages/domain/journey.py's pure logic with persistence
(JourneyRepository) and with the domain data that `system`-kind completion checks read
(JOURNEY_MANIFEST.md §6). This is the ONLY place the manifest's `system` check keys are
interpreted; the manifest and the YAML-loading layer know nothing about what a check
actually queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from packages.domain.enums import SCRIPT_INTELLIGENCE_GRAPH_ID, CandidateStatus
from packages.domain.errors import InvalidStateError, TenantAccessViolation, ValidationFailure
from packages.domain.journey import (
    ITEM_STATUSES,
    Group,
    Section,
    Subpoint,
    derive_group_status,
    derive_section_status,
    group_by_id,
    group_id_for_subpoint,
    group_passes_for_gating,
    is_released,
    resolve_applicability,
    sections,
)
from packages.persistence.repositories import (
    AssetRepository,
    CandidateRepository,
    FilmBibleRepository,
    JourneyRepository,
    ProjectRepository,
    ResearchRepository,
    WorkflowRunRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext

# A production project has no shots table yet (D7/D9); until then the shot_method_in
# exception in applicability (JRN-07.4) simply never triggers -- there are no shots to
# have a method at all. This keeps the interface the resolver expects (a frozenset of
# methods actually present on the project) stable, so swapping in a real query later
# is a one-line change here, not a change to the resolver or its callers.
_NO_SHOT_METHODS: frozenset[str] = frozenset()

#: V2 is not built yet; every project sees only FD-V1 groups until the first release
#: that ships something behind this, per Master Prompt "no screen implies a feature
#: before it is built". Kept as a single constant rather than a setting because flipping
#: it is a release event (D-stage completion), not an environment knob.
V2_ENABLED = False


def _some_and_none_pending(*candidate_lists) -> bool:
    """A 'no pending candidates' review gate must not be vacuously true before any
    candidate has ever been generated: a brand-new project with zero candidates has
    trivially "no pending" ones, but nothing has actually been reviewed. Require that at
    least one candidate exists, and that none of them are still proposed."""
    all_candidates = [c for lst in candidate_lists for c in lst]
    if not all_candidates:
        return False
    return not any(c.status == CandidateStatus.PROPOSED.value for c in all_candidates)


@dataclass(frozen=True)
class SubpointView:
    subpoint: Subpoint
    status: str
    not_applicable_reason: str | None
    evidence_refs: list
    notes: str | None


@dataclass(frozen=True)
class GroupView:
    group: Group
    status: str
    applies: bool
    applicability_reason: str | None
    subpoints: list[SubpointView]
    can_act: bool
    can_approve: bool


@dataclass(frozen=True)
class SectionView:
    section: Section
    status: str
    groups: list[GroupView]
    can_continue: bool


class JourneyService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.journey = JourneyRepository(db)
        self.authz = AuthzService(db)
        self.runs = WorkflowRunRepository(db)
        self.candidates = CandidateRepository(db)
        self.research = ResearchRepository(db)
        self.film_bible = FilmBibleRepository(db)
        self.assets = AssetRepository(db)

    # -- reading -----------------------------------------------------------------

    def get_journey(self, actor: ActorContext, project_id: str) -> list[SectionView]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)

        states = self.journey.get_item_states(project_id)
        stale_ids = self.journey.stale_jrn_ids(project_id)
        system_check_cache: dict[str, bool] = {}

        result: list[SectionView] = []
        for section in sections():
            group_views: list[GroupView] = []
            for group in section.groups:
                if not is_released(group, v2_enabled=V2_ENABLED):
                    continue
                group_views.append(
                    self._build_group_view(project, group, states, stale_ids, system_check_cache, actor)
                )
            group_statuses = [gv.status for gv in group_views]
            section_status = derive_section_status(group_statuses)
            result.append(
                SectionView(
                    section=section,
                    status=section_status,
                    groups=group_views,
                    can_continue=section_status == "ready_to_continue",
                )
            )
        return result

    def _build_group_view(
        self,
        project,
        group: Group,
        states: dict,
        stale_ids: set[str],
        system_check_cache: dict[str, bool],
        actor: ActorContext,
    ) -> GroupView:
        applies, reason = resolve_applicability(
            group, production_mode=project.production_mode, shot_methods=_NO_SHOT_METHODS
        )

        subpoint_views: list[SubpointView] = []
        subpoint_statuses: list[str] = []
        for subpoint in group.subpoints:
            effective_status = self._effective_subpoint_status(
                project, group, subpoint, states, stale_ids, system_check_cache
            )
            row = states.get(subpoint.id)
            subpoint_views.append(
                SubpointView(
                    subpoint=subpoint,
                    status=effective_status,
                    not_applicable_reason=row.not_applicable_reason if row else None,
                    evidence_refs=row.evidence_refs if row else [],
                    notes=row.notes if row else None,
                )
            )
            subpoint_statuses.append(effective_status)

        group_status = derive_group_status(subpoint_statuses, applies=applies, mode_na_reason=reason)

        can_act = self._has_capability(actor, project, group.act_capability)
        can_approve = group.approval_capability is None or self._has_capability(
            actor, project, group.approval_capability
        )
        return GroupView(
            group=group,
            status=group_status,
            applies=applies,
            applicability_reason=reason,
            subpoints=subpoint_views,
            can_act=can_act,
            can_approve=can_approve,
        )

    def _has_capability(self, actor: ActorContext, project, capability: str) -> bool:
        try:
            self.authz.require(actor, capability, project)
            return True
        except TenantAccessViolation:
            return False

    def _effective_subpoint_status(self, project, group: Group, subpoint: Subpoint, states, stale_ids, cache) -> str:
        if subpoint.id in stale_ids:
            return "stale"
        row = states.get(subpoint.id)
        persisted = row.status if row else "not_started"

        check = group.completion_check
        if check["kind"] == "system" and subpoint.key == "validate":
            # The `validate` subpoint's completion is DERIVED from domain state for a
            # system-checked group; the `prepare` subpoint stays a plain manual status
            # (there is always some human step of reviewing before the system check can
            # even be meaningful, e.g. picking which script asset to ingest).
            key = check["key"]
            if key not in cache:
                cache[key] = self._evaluate_system_check(project.id, key)
            return "completed" if cache[key] else persisted
        return persisted

    def _evaluate_system_check(self, project_id: str, key: str) -> bool:
        if key == "screenplay_asset_present":
            return any(a.asset_type == "script" for a in self.assets.list_for_project(project_id))
        if key == "workflow_completed:script_intelligence":
            return self.runs.exists_completed(project_id, SCRIPT_INTELLIGENCE_GRAPH_ID)
        if key == "no_pending_candidates:script_intelligence":
            scenes = self.candidates.scenes_for_project(project_id)
            entities = self.candidates.entities_for_project(project_id)
            return _some_and_none_pending(scenes, entities)
        if key == "research_questions_present":
            return len(self.research.list_questions(project_id)) > 0
        if key == "no_pending_candidates:historical_research":
            claims = self.candidates.claims_for_project(project_id)
            questions = self.candidates.questions_for_project(project_id)
            return _some_and_none_pending(claims, questions)
        if key == "approved_rules_present:film_bible":
            return len(self.film_bible.list_rules_for_project(project_id)) > 0
        if key == "no_pending_candidates:storyboard_intelligence":
            panels = self.candidates.storyboard_panels_for_project(project_id)
            return _some_and_none_pending(panels)
        raise ValidationFailure(f"Unknown system check key: {key!r}")

    # -- acting on an item ---------------------------------------------------------

    def act_on_item(
        self,
        actor: ActorContext,
        project_id: str,
        jrn_subpoint_id: str,
        action: str,
        *,
        not_applicable_reason: str | None = None,
        evidence_refs: list | None = None,
        notes: str | None = None,
    ) -> SubpointView:
        """``action`` is one of: draft, complete, request_review, not_applicable.

        Opening a screen never completes anything (JOURNEY_MANIFEST.md §6): this method
        is the only way a subpoint's status changes, and it is only ever called by an
        explicit user action, never a page view.
        """
        project = self.projects.get_scoped(project_id, actor.org_id)
        group_id = group_id_for_subpoint(jrn_subpoint_id)
        group = group_by_id(group_id)
        subpoint = next((s for s in group.subpoints if s.id == jrn_subpoint_id), None)
        if subpoint is None:
            raise ValidationFailure(f"Unknown journey subpoint id: {jrn_subpoint_id!r}")

        required_capability = group.act_capability
        if action == "request_review" and subpoint.kind == "review_gate" and group.approval_capability:
            # Requesting review is still an "act" (the preparer's capability); deciding
            # it is the separate approval_capability, exercised by complete below.
            required_capability = group.act_capability
        self.authz.require(actor, required_capability, project)

        if group.completion_check["kind"] == "system" and subpoint.key == "validate" and action == "complete":
            raise InvalidStateError(
                "This step's completion is derived automatically from project data; it cannot be marked complete by hand."
            )

        status_map = {
            "draft": "in_progress",
            "complete": "completed",
            "request_review": "review_required",
            "not_applicable": "not_applicable",
        }
        if action not in status_map:
            raise ValidationFailure(f"Unknown journey action: {action!r}")
        new_status = status_map[action]

        if action == "not_applicable":
            if group.na_policy == "never":
                raise InvalidStateError(f"{group.id} can never be marked not applicable.")
            if group.na_policy == "reason_required" and not not_applicable_reason:
                raise ValidationFailure("A reason is required to mark this item not applicable.")

        if action == "complete" and subpoint.kind == "review_gate" and group.approval_capability:
            # The validate subpoint, when it represents a real approval, needs the
            # approval capability specifically, not just the general act_capability
            # (e.g. completing JRN-02.4.2 needs screenplay.approve_lock, not canon.propose).
            self.authz.require(actor, group.approval_capability, project)

        assert new_status in ITEM_STATUSES
        row = self.journey.upsert_item_state(
            project.id,
            project.organization_id,
            jrn_subpoint_id,
            status=new_status,
            actor_id=actor.user_id,
            not_applicable_reason=not_applicable_reason,
            evidence_refs=evidence_refs,
            notes=notes,
        )
        if new_status != "stale":
            self.journey.resolve_stale(project.id, jrn_subpoint_id, actor_id=actor.user_id)
        self.db.commit()
        return SubpointView(
            subpoint=subpoint,
            status=row.status,
            not_applicable_reason=row.not_applicable_reason,
            evidence_refs=row.evidence_refs,
            notes=row.notes,
        )

    # -- section continue -----------------------------------------------------------

    def continue_section(self, actor: ActorContext, project_id: str, jrn_section_id: str) -> dict[str, Any]:
        """Persist the explicit 'Continue to Next Section' transition. The server never
        advances a section on its own (gating.auto_advance: false); this is the only
        write path for a journey_section_events row."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)

        views = self.get_journey(actor, project_id)
        view = next((v for v in views if v.section.id == jrn_section_id), None)
        if view is None:
            raise ValidationFailure(f"Unknown journey section id: {jrn_section_id!r}")
        if not view.can_continue:
            blockers = [
                {"group_id": g.group.id, "title": g.group.title, "status": g.status}
                for g in view.groups
                if not group_passes_for_gating(g.status)
            ]
            raise InvalidStateError(f"Section {jrn_section_id} is not ready to continue: {blockers}")

        snapshot = {g.group.id: g.status for g in view.groups}
        self.journey.record_section_continue(project.id, project.organization_id, jrn_section_id, actor.user_id, snapshot)
        self.db.commit()
        return {"section_id": jrn_section_id, "status": "completed", "group_statuses": snapshot}
