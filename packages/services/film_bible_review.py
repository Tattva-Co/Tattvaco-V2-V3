"""Canonical-state operations for Film Bible review cycle (Workflow G-04).

LangGraph nodes orchestrate; these methods own every write to canonical tables
(ADR-001 invariant 2). Each public method is one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy.orm import Session

from packages.domain.enums import (
    FILM_BIBLE_APPROVAL_SCOPE,
    ApprovalStatus,
    AuditAction,
    CandidateStatus,
    WorkflowStatus,
)
from packages.domain.errors import ValidationFailure
from packages.domain.invariants import assert_expected_version
from packages.persistence.models import (
    ApprovalRequestModel,
    FilmBibleRuleCandidateModel,
    FilmBibleRuleModel,
    ProjectVersionModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CandidateRepository,
    FilmBibleRepository,
    ProjectRepository,
    ResearchRepository,
    WorkflowRunRepository,
)


@dataclass(frozen=True)
class RunScope:
    run_id: str
    project_id: str
    org_id: str
    generator_mode: str


@dataclass
class ProposedFilmBibleCandidates:
    approval_request_id: str
    rules: list[dict[str, Any]]


class FilmBibleReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.runs = WorkflowRunRepository(db)
        self.approvals = ApprovalRepository(db)
        self.candidates = CandidateRepository(db)
        self.film_bible = FilmBibleRepository(db)
        self.research = ResearchRepository(db)
        self.audit = AuditRepository(db)

    def validate_scope(self, run_id: str) -> RunScope:
        run = self.runs.get(run_id)
        project = self.projects.get_scoped(run.project_id, run.organization_id)
        assert_expected_version(project.current_version, run.expected_project_version)
        return RunScope(
            run_id=run.id,
            project_id=project.id,
            org_id=project.organization_id,
            generator_mode=run.generator_mode,
        )

    def propose_candidates(
        self,
        run_id: str,
        rules: Sequence[dict[str, Any]],
        actor_id: str | None = None,
    ) -> ProposedFilmBibleCandidates:
        if not rules:
            raise ValidationFailure("No Film Bible rules synthesized")

        scope = self.validate_scope(run_id)
        project = self.projects.get_scoped(scope.project_id, scope.org_id)
        effective_actor = actor_id or project.created_by

        rule_rows: list[FilmBibleRuleCandidateModel] = []
        for r in rules:
            row = FilmBibleRuleCandidateModel(
                workflow_run_id=scope.run_id,
                project_id=scope.project_id,
                organization_id=scope.org_id,
                category=r["category"],
                title=r["title"],
                rule_text=r["rule_text"],
                negative_prompt_guidance=r.get("negative_prompt_guidance"),
                strictness=r.get("strictness", "guideline"),
                suggested_claim_statement=r.get("suggested_claim_statement"),
                confidence=float(r.get("confidence", 0.9)),
                conflict_warning=r.get("conflict_warning"),
                status=CandidateStatus.PROPOSED.value,
                generator_mode=scope.generator_mode,
            )
            self.candidates.add_film_bible_rule(row)
            rule_rows.append(row)

        approval = self.approvals.add(
            ApprovalRequestModel(
                workflow_run_id=scope.run_id,
                organization_id=scope.org_id,
                project_id=scope.project_id,
                scope=FILM_BIBLE_APPROVAL_SCOPE,
                candidate_summary={
                    "rule_count": len(rule_rows),
                    "rules": [
                        {
                            "id": row.id,
                            "category": row.category,
                            "title": row.title,
                            "strictness": row.strictness,
                            "conflict_warning": row.conflict_warning,
                        }
                        for row in rule_rows
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
                "rule_count": len(rule_rows),
                "scope": FILM_BIBLE_APPROVAL_SCOPE,
            },
        )
        self.db.commit()

        return ProposedFilmBibleCandidates(
            approval_request_id=approval.id,
            rules=[{**r, "candidate_id": row.id} for r, row in zip(rules, rule_rows, strict=False)],
        )

    def commit_approved_candidates(
        self,
        run_id: str,
        decision_notes: str | None,
        decided_by: str | None,
        approved_rule_ids: Sequence[str] | None = None,
    ) -> int:
        scope = self.validate_scope(run_id)
        # Lock the project row so concurrent approvals cannot produce duplicate versions.
        project = self.projects.get_scoped(scope.project_id, scope.org_id, for_update=True)
        assert_expected_version(project.current_version, self.runs.get(run_id).expected_project_version)
        rule_rows = self.candidates.film_bible_rules_for_run(run_id)

        target_rule_ids = set(approved_rule_ids) if approved_rule_ids is not None else {r.id for r in rule_rows}

        new_version = project.current_version + 1
        actor_id = decided_by or project.created_by

        # Map claims by statement to link historical_claim_id if matched
        claims = self.research.list_claims(scope.project_id)
        claims_by_stmt = {c.statement: c.id for c in claims}

        committed_count = 0
        for r in rule_rows:
            if r.id in target_rule_ids:
                r.status = CandidateStatus.APPROVED.value
                matched_claim_id = claims_by_stmt.get(r.suggested_claim_statement) if r.suggested_claim_statement else None
                model = FilmBibleRuleModel(
                    project_id=scope.project_id,
                    organization_id=scope.org_id,
                    project_version=new_version,
                    category=r.category,
                    title=r.title,
                    rule_text=r.rule_text,
                    negative_prompt_guidance=r.negative_prompt_guidance,
                    strictness=r.strictness,
                    historical_claim_id=matched_claim_id,
                    rationale=f"Approved in Workflow run {run_id}. {decision_notes or ''}".strip(),
                )
                self.film_bible.add_rule(model)
                committed_count += 1
            else:
                r.status = CandidateStatus.REJECTED.value

        project.current_version = new_version
        self.projects.add_version(
            ProjectVersionModel(
                project_id=project.id,
                organization_id=project.organization_id,
                version_number=new_version,
                branch_name="main",
                commit_message=f"Film Bible visual-world rules approved: {committed_count} rules committed ({decision_notes or 'no notes'})",
                snapshot_data={
                    "committed_rules": committed_count,
                    "rejected_rules": len(rule_rows) - committed_count,
                    "workflow_run_id": run_id,
                },
                committed_by=actor_id,
            )
        )
        self.runs.set_status(run_id, WorkflowStatus.COMPLETED.value)

        self.audit.record(
            project_id=scope.project_id,
            organization_id=scope.org_id,
            actor_id=actor_id,
            action=AuditAction.FILM_BIBLE_COMMITTED,
            target_type="project_version",
            target_id=str(new_version),
            details={
                "workflow_run_id": run_id,
                "committed_rules": committed_count,
                "version": new_version,
            },
        )
        self.db.commit()
        return new_version

    def reject_candidates(
        self,
        run_id: str,
        decision_notes: str | None,
        decided_by: str | None,
    ) -> None:
        scope = self.validate_scope(run_id)
        project = self.projects.get_scoped(scope.project_id, scope.org_id)
        effective_actor = decided_by or project.created_by

        for r in self.candidates.film_bible_rules_for_run(run_id):
            r.status = CandidateStatus.REJECTED.value

        self.runs.set_status(run_id, WorkflowStatus.REJECTED.value)

        self.audit.record(
            project_id=scope.project_id,
            organization_id=scope.org_id,
            actor_id=effective_actor,
            action=AuditAction.FILM_BIBLE_REJECTED,
            target_type="workflow_run",
            target_id=run_id,
            details={"notes": decision_notes},
        )
        self.db.commit()

