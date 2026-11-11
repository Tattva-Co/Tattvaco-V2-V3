"""Canonical-state operations for Historical Research review cycle.

LangGraph nodes orchestrate; these methods own every write to canonical tables
(ADR-001 invariant 2). Each public method is one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy.orm import Session

from packages.domain.enums import (
    HISTORICAL_RESEARCH_APPROVAL_SCOPE,
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
    ResearchClaimCandidateModel,
    ResearchClaimModel,
    ResearchQuestionCandidateModel,
    ResearchQuestionModel,
    ResearchSourceModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CandidateRepository,
    ProjectRepository,
    WorkflowRunRepository,
)


@dataclass(frozen=True)
class RunScope:
    run_id: str
    project_id: str
    org_id: str
    generator_mode: str


@dataclass
class ProposedResearchCandidates:
    approval_request_id: str
    claims: list[dict[str, Any]]
    questions: list[dict[str, Any]]


class ResearchReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.runs = WorkflowRunRepository(db)
        self.approvals = ApprovalRepository(db)
        self.candidates = CandidateRepository(db)
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
        claims: Sequence[dict[str, Any]],
        questions: Sequence[dict[str, Any]],
        actor_id: str | None = None,
    ) -> ProposedResearchCandidates:
        if not claims and not questions:
            raise ValidationFailure("No research claims or questions extracted")

        scope = self.validate_scope(run_id)
        project = self.projects.get_scoped(scope.project_id, scope.org_id)
        effective_actor = actor_id or project.created_by

        claim_rows: list[ResearchClaimCandidateModel] = []
        for c in claims:
            row = ResearchClaimCandidateModel(
                workflow_run_id=scope.run_id,
                project_id=scope.project_id,
                organization_id=scope.org_id,
                claim_class=c.get("claim_class", "historical_fact"),
                statement=c["statement"],
                era_or_date=c.get("era_or_date"),
                location=c.get("location"),
                confidence=float(c.get("confidence", 0.9)),
                source_title=c.get("source_title", "General Historical Record"),
                source_tier=c.get("source_tier", "tier_2_scholarly"),
                source_locator=c.get("source_locator"),
                status=CandidateStatus.PROPOSED.value,
                generator_mode=scope.generator_mode,
            )
            self.candidates.add_claim(row)
            claim_rows.append(row)

        question_rows: list[ResearchQuestionCandidateModel] = []
        for q in questions:
            row = ResearchQuestionCandidateModel(
                workflow_run_id=scope.run_id,
                project_id=scope.project_id,
                organization_id=scope.org_id,
                text=q["text"],
                category=q.get("category", "general"),
                status=CandidateStatus.PROPOSED.value,
                generator_mode=scope.generator_mode,
            )
            self.candidates.add_question(row)
            question_rows.append(row)

        approval = self.approvals.add(
            ApprovalRequestModel(
                workflow_run_id=scope.run_id,
                organization_id=scope.org_id,
                project_id=scope.project_id,
                scope=HISTORICAL_RESEARCH_APPROVAL_SCOPE,
                candidate_summary={
                    "claims_count": len(claim_rows),
                    "questions_count": len(question_rows),
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
                "claims_count": len(claim_rows),
                "questions_count": len(question_rows),
                "scope": HISTORICAL_RESEARCH_APPROVAL_SCOPE,
            },
        )
        self.db.commit()

        return ProposedResearchCandidates(
            approval_request_id=approval.id,
            claims=[{**c, "candidate_id": r.id} for c, r in zip(claims, claim_rows, strict=False)],
            questions=[{**q, "candidate_id": r.id} for q, r in zip(questions, question_rows, strict=False)],
        )

    def commit_approved_candidates(
        self,
        run_id: str,
        decision_notes: str | None,
        decided_by: str | None,
        approved_claim_ids: Sequence[str] | None = None,
        approved_question_ids: Sequence[str] | None = None,
    ) -> int:
        scope = self.validate_scope(run_id)
        # Lock the project row so concurrent approvals cannot produce duplicate versions
        # (docs/audit/08 PERF-06). validate_scope's own read happened before this lock was
        # acquired, so the version is re-checked once the lock is held.
        project = self.projects.get_scoped(scope.project_id, scope.org_id, for_update=True)
        assert_expected_version(project.current_version, self.runs.get(run_id).expected_project_version)
        claim_rows = self.candidates.claims_for_run(run_id)
        question_rows = self.candidates.questions_for_run(run_id)

        target_claim_ids = set(approved_claim_ids) if approved_claim_ids is not None else {c.id for c in claim_rows}
        target_question_ids = (
            set(approved_question_ids) if approved_question_ids is not None else {q.id for q in question_rows}
        )

        new_version = project.current_version + 1
        actor_id = decided_by or project.created_by

        # Commit approved claims and create source records if needed
        sources_cache: dict[str, str] = {}
        committed_claims = 0
        for c in claim_rows:
            if c.id in target_claim_ids:
                c.status = CandidateStatus.APPROVED.value
                source_id = None
                if c.source_title:
                    if c.source_title not in sources_cache:
                        source_row = ResearchSourceModel(
                            project_id=scope.project_id,
                            organization_id=scope.org_id,
                            project_version=new_version,
                            title=c.source_title,
                            tier=c.source_tier,
                            locator=c.source_locator,
                        )
                        self.db.add(source_row)
                        self.db.flush()
                        sources_cache[c.source_title] = source_row.id
                    source_id = sources_cache[c.source_title]

                claim_model = ResearchClaimModel(
                    project_id=scope.project_id,
                    organization_id=scope.org_id,
                    project_version=new_version,
                    claim_class=c.claim_class,
                    statement=c.statement,
                    era_or_date=c.era_or_date,
                    location=c.location,
                    confidence=c.confidence,
                    source_id=source_id,
                    status=CandidateStatus.APPROVED.value,
                )
                self.db.add(claim_model)
                committed_claims += 1
            else:
                c.status = CandidateStatus.REJECTED.value

        # Commit approved questions
        committed_questions = 0
        for q in question_rows:
            if q.id in target_question_ids:
                q.status = CandidateStatus.APPROVED.value
                q_model = ResearchQuestionModel(
                    project_id=scope.project_id,
                    organization_id=scope.org_id,
                    project_version=new_version,
                    text=q.text,
                    category=q.category,
                    status="open",
                )
                self.db.add(q_model)
                committed_questions += 1
            else:
                q.status = CandidateStatus.REJECTED.value

        project.current_version = new_version
        version_row = ProjectVersionModel(
            project_id=project.id,
            organization_id=project.organization_id,
            version_number=new_version,
            branch_name="main",
            commit_message=f"Historical research committed: {committed_claims} claims, {committed_questions} questions",
            committed_by=actor_id,
            snapshot_data={
                "claims_committed": committed_claims,
                "questions_committed": committed_questions,
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
            action=AuditAction.RESEARCH_COMMITTED,
            target_type="project_version",
            target_id=version_row.id,
            details={
                "new_version": new_version,
                "claims_committed": committed_claims,
                "questions_committed": committed_questions,
                "workflow_run_id": run_id,
            },
        )
        self.db.commit()
        return new_version

    def reject_candidates(self, run_id: str, notes: str | None, actor_id: str | None) -> int:
        scope = self.validate_scope(run_id)
        project = self.projects.get_scoped(scope.project_id, scope.org_id)

        for c in self.candidates.claims_for_run(run_id):
            c.status = CandidateStatus.REJECTED.value
        for q in self.candidates.questions_for_run(run_id):
            q.status = CandidateStatus.REJECTED.value

        run = self.runs.get(run_id)
        run.status = WorkflowStatus.REJECTED.value

        actor = actor_id or project.created_by
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor,
            action=AuditAction.RESEARCH_REJECTED,
            target_type="workflow_run",
            target_id=run.id,
            details={"notes": notes, "status": "rejected"},
        )
        self.db.commit()
        return project.current_version

