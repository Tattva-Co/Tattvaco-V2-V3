"""Script Intelligence LangGraph StateGraph (Workflow G-01).

Implements parsing, candidate generation, human approval interruption,
and canonical domain state promotion with versioning and audit trails.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from packages.domain.invariants import (
    assert_expected_version,
    assert_project_scope,
    DomainInvariantError,
)
from packages.persistence.database import SessionLocal
from packages.persistence.models import (
    ApprovalRequestModel,
    AuditEventModel,
    EntityCandidateModel,
    EntityModel,
    ProjectModel,
    ProjectVersionModel,
    SceneCandidateModel,
    SceneModel,
    WorkflowRunModel,
)
from packages.workflows.script_intelligence.parser import ScreenplayParser
from packages.workflows.script_intelligence.state import ScriptIntelligenceState


def parse_script_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Parse raw script text into scenes and entities."""
    raw_text = state.get("raw_script_text", "")
    if not raw_text.strip():
        return {
            "error_message": "Script text is empty",
            "completed": False,
        }

    parser = ScreenplayParser()
    scenes, entities = parser.parse(raw_text)

    return {
        "extracted_scenes": scenes,
        "extracted_entities": entities,
    }


def generate_candidates_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Persist extracted candidates and create human approval request."""
    db = SessionLocal()
    try:
        project_id = state["project_id"]
        organization_id = state["organization_id"]
        workflow_run_id = state["workflow_run_id"]
        actor_id = state["actor_id"]

        # 1. Create SceneCandidate rows
        created_scene_candidates: List[Dict[str, Any]] = []
        for s in state.get("extracted_scenes", []):
            sc = SceneCandidateModel(
                workflow_run_id=workflow_run_id,
                project_id=project_id,
                scene_number=s["scene_number"],
                heading=s["heading"],
                setting=s["setting"],
                location_name=s["location_name"],
                time_of_day=s["time_of_day"],
                summary=s["summary"],
                source_locator=s["source_locator"],
                characters_present=s["characters_present"],
                status="proposed",
            )
            db.add(sc)
            db.flush()
            created_scene_candidates.append({
                "id": sc.id,
                "scene_number": sc.scene_number,
                "heading": sc.heading,
                "summary": sc.summary,
            })

        # 2. Create EntityCandidate rows
        created_entity_candidates: List[Dict[str, Any]] = []
        for e in state.get("extracted_entities", []):
            ec = EntityCandidateModel(
                workflow_run_id=workflow_run_id,
                project_id=project_id,
                name=e["name"],
                category=e["category"],
                description=e["description"],
                source_locator=e["source_locator"],
                confidence=e.get("confidence", 0.9),
                status="proposed",
            )
            db.add(ec)
            db.flush()
            created_entity_candidates.append({
                "id": ec.id,
                "name": ec.name,
                "category": ec.category,
                "confidence": ec.confidence,
            })

        # 3. Create ApprovalRequest row
        approval = ApprovalRequestModel(
            workflow_run_id=workflow_run_id,
            project_id=project_id,
            organization_id=organization_id,
            scope="script_intelligence_candidates",
            candidate_summary={
                "scene_count": len(created_scene_candidates),
                "entity_count": len(created_entity_candidates),
                "scenes": created_scene_candidates,
                "entities": created_entity_candidates,
            },
            status="pending",
        )
        db.add(approval)
        db.flush()

        # 4. Record Audit Event
        audit = AuditEventModel(
            project_id=project_id,
            organization_id=organization_id,
            actor_id=actor_id,
            action="candidates_extracted",
            target_type="approval_request",
            target_id=approval.id,
            details={
                "workflow_run_id": workflow_run_id,
                "scenes_proposed": len(created_scene_candidates),
                "entities_proposed": len(created_entity_candidates),
            },
        )
        db.add(audit)

        # 5. Update workflow run status to awaiting_approval
        run = db.query(WorkflowRunModel).filter_by(id=workflow_run_id).first()
        if run:
            run.status = "awaiting_approval"

        db.commit()

        return {
            "approval_request_id": approval.id,
            "approval_status": "pending",
            "extracted_scenes": [
                {**s, "candidate_id": sc["id"]}
                for s, sc in zip(state.get("extracted_scenes", []), created_scene_candidates)
            ],
            "extracted_entities": [
                {**e, "candidate_id": ec["id"]}
                for e, ec in zip(state.get("extracted_entities", []), created_entity_candidates)
            ],
        }
    finally:
        db.close()


def human_approval_interrupt_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Interrupt the workflow to require explicit human review and approval."""
    # If approval has not been given yet, trigger an interrupt
    approval_status = state.get("approval_status", "pending")
    if approval_status == "pending":
        # LangGraph interrupt: execution pauses here until resumed with human decision
        human_decision = interrupt({
            "message": "Human approval required for Script Intelligence candidates",
            "approval_request_id": state.get("approval_request_id"),
            "scenes": state.get("extracted_scenes", []),
            "entities": state.get("extracted_entities", []),
        })

        # When resumed, human_decision contains the approval payload
        if isinstance(human_decision, dict):
            return {
                "approval_status": human_decision.get("decision", "rejected"),
                "decision_notes": human_decision.get("notes"),
                "decided_by": human_decision.get("actor_id"),
                "approved_scene_ids": human_decision.get("approved_scene_ids", []),
                "approved_entity_ids": human_decision.get("approved_entity_ids", []),
            }

    return {}


def should_commit(
    state: ScriptIntelligenceState,
) -> Literal["commit_canonical_node", "record_rejection_node"]:
    """Conditional edge: approved candidates are committed, anything else is a rejection."""
    if state.get("approval_status") == "approved":
        return "commit_canonical_node"
    return "record_rejection_node"


def _record_decision(
    db, workflow_run_id: str, decision: str, actor_id: str, notes: Optional[str]
) -> None:
    approval = (
        db.query(ApprovalRequestModel)
        .filter_by(workflow_run_id=workflow_run_id, status="pending")
        .first()
    )
    if approval:
        approval.status = "decided"
        approval.decision = decision
        approval.decision_notes = notes
        approval.decided_by = actor_id
        approval.decided_at = datetime.now(timezone.utc)


def record_rejection_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Close a rejected review: candidates rejected, run rejected, project untouched."""
    db = SessionLocal()
    try:
        workflow_run_id = state["workflow_run_id"]
        actor_id = state.get("decided_by") or state["actor_id"]

        _record_decision(db, workflow_run_id, "rejected", actor_id, state.get("decision_notes"))
        for model in (SceneCandidateModel, EntityCandidateModel):
            db.query(model).filter(model.workflow_run_id == workflow_run_id).update(
                {"status": "rejected"}, synchronize_session=False
            )

        run = db.query(WorkflowRunModel).filter_by(id=workflow_run_id).first()
        if run:
            run.status = "rejected"

        db.add(
            AuditEventModel(
                project_id=state["project_id"],
                organization_id=state["organization_id"],
                actor_id=actor_id,
                action="script_intelligence_rejected",
                target_type="workflow_run",
                target_id=workflow_run_id,
                details={"notes": state.get("decision_notes")},
            )
        )
        db.commit()
        return {"completed": True}
    finally:
        db.close()


def commit_canonical_node(state: ScriptIntelligenceState) -> Dict[str, Any]:
    """Promote approved candidates to canonical project entities and advance project version."""
    db = SessionLocal()
    try:
        project_id = state["project_id"]
        organization_id = state["organization_id"]
        workflow_run_id = state["workflow_run_id"]
        actor_id = state.get("decided_by") or state["actor_id"]

        # Validate project scope and version invariant
        project = db.query(ProjectModel).filter_by(id=project_id, organization_id=organization_id).first()
        if not project:
            raise DomainInvariantError(f"Project {project_id} not found in org {organization_id}")

        assert_expected_version(project.current_version, state.get("expected_project_version", project.current_version))

        approved_scene_ids = set(state.get("approved_scene_ids", []))
        approved_entity_ids = set(state.get("approved_entity_ids", []))

        next_version = project.current_version + 1

        # 1. Promote approved scene candidates
        promoted_scenes_count = 0
        scene_candidates = db.query(SceneCandidateModel).filter(
            SceneCandidateModel.workflow_run_id == workflow_run_id
        ).all()
        for sc in scene_candidates:
            if not approved_scene_ids or sc.id in approved_scene_ids:
                sc.status = "approved"
                canonical_scene = SceneModel(
                    project_id=project_id,
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
                db.add(canonical_scene)
                promoted_scenes_count += 1
            else:
                sc.status = "rejected"

        # 2. Promote approved entity candidates
        promoted_entities_count = 0
        entity_candidates = db.query(EntityCandidateModel).filter(
            EntityCandidateModel.workflow_run_id == workflow_run_id
        ).all()
        for ec in entity_candidates:
            if not approved_entity_ids or ec.id in approved_entity_ids:
                ec.status = "approved"
                canonical_entity = EntityModel(
                    project_id=project_id,
                    name=ec.name,
                    category=ec.category,
                    description=ec.description,
                    source_locator=ec.source_locator,
                    project_version=next_version,
                )
                db.add(canonical_entity)
                promoted_entities_count += 1
            else:
                ec.status = "rejected"

        # 3. Increment project version & record snapshot
        project.current_version = next_version
        version_record = ProjectVersionModel(
            project_id=project_id,
            version_number=next_version,
            branch_name="main",
            commit_message=f"Script Intelligence extraction: {promoted_scenes_count} scenes, {promoted_entities_count} entities",
            committed_by=actor_id,
            snapshot_data={
                "scenes_count": promoted_scenes_count,
                "entities_count": promoted_entities_count,
                "workflow_run_id": workflow_run_id,
            },
        )
        db.add(version_record)
        db.flush()  # assign version_record.id before the audit row references it

        # 4. Record the approval decision
        _record_decision(db, workflow_run_id, "approved", actor_id, state.get("decision_notes"))

        # 5. Record Audit Event
        audit = AuditEventModel(
            project_id=project_id,
            organization_id=organization_id,
            actor_id=actor_id,
            action="script_intelligence_committed",
            target_type="project_version",
            target_id=version_record.id,
            details={
                "previous_version": next_version - 1,
                "new_version": next_version,
                "promoted_scenes": promoted_scenes_count,
                "promoted_entities": promoted_entities_count,
            },
        )
        db.add(audit)

        # 6. Mark workflow run completed
        run = db.query(WorkflowRunModel).filter_by(id=workflow_run_id).first()
        if run:
            run.status = "completed"
            run.output_refs = {
                "new_version": next_version,
                "scenes_count": promoted_scenes_count,
                "entities_count": promoted_entities_count,
            }

        db.commit()

        return {
            "new_project_version": next_version,
            "completed": True,
        }
    finally:
        db.close()


def build_script_intelligence_graph() -> StateGraph:
    """Build and compile the Script Intelligence StateGraph."""
    workflow = StateGraph(ScriptIntelligenceState)

    workflow.add_node("parse_script_node", parse_script_node)
    workflow.add_node("generate_candidates_node", generate_candidates_node)
    workflow.add_node("human_approval_interrupt_node", human_approval_interrupt_node)
    workflow.add_node("commit_canonical_node", commit_canonical_node)
    workflow.add_node("record_rejection_node", record_rejection_node)

    workflow.add_edge(START, "parse_script_node")
    workflow.add_edge("parse_script_node", "generate_candidates_node")
    workflow.add_edge("generate_candidates_node", "human_approval_interrupt_node")
    workflow.add_conditional_edges(
        "human_approval_interrupt_node",
        should_commit,
        {
            "commit_canonical_node": "commit_canonical_node",
            "record_rejection_node": "record_rejection_node",
        },
    )
    workflow.add_edge("commit_canonical_node", END)
    workflow.add_edge("record_rejection_node", END)

    return workflow
