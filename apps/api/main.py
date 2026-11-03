"""FastAPI Application Server for Tattva AI Film Director.

Provides tenant-scoped endpoints for projects, assets, script parsing workflows,
human approval gates, canonical versions, and audit trails.
"""

from datetime import datetime, timezone
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from packages.domain.invariants import (
    assert_expected_version,
    assert_project_scope,
    DomainInvariantError,
    TenantAccessViolation,
    VersionConflictError,
)
from packages.persistence.database import get_db
from packages.persistence.models import (
    ApprovalRequestModel,
    AssetModel,
    AuditEventModel,
    EntityCandidateModel,
    EntityModel,
    OrganizationModel,
    OutboxTaskModel,
    ProjectModel,
    ProjectVersionModel,
    SceneCandidateModel,
    SceneModel,
    UserModel,
    WorkflowRunModel,
)
from packages.storage.service import LocalFileSystemStorageService, StorageService
from packages.workflows.script_intelligence.graph import build_script_intelligence_graph
from packages.workflows.checkpointer import get_checkpointer

app = FastAPI(
    title="Tattva AI Film Director API",
    version="1.0.0",
    description="Greenfield API boundary for film intelligence lifecycle and workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage dependency
_storage_service = LocalFileSystemStorageService(
    root_dir=os.getenv("STORAGE_LOCAL_ROOT", "./data/storage")
)


def get_storage() -> StorageService:
    return _storage_service


# ------------------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------------------

class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    logline: Optional[str] = None
    genre: Optional[str] = None
    organization_id: Optional[str] = None
    actor_id: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    logline: Optional[str]
    genre: Optional[str]
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WorkflowTriggerRequest(BaseModel):
    script_asset_id: str
    actor_id: Optional[str] = None
    sync_execution: bool = True  # True allows direct execution for responsive dev


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    actor_id: str
    notes: Optional[str] = None
    approved_scene_ids: List[str] = Field(default_factory=list)
    approved_entity_ids: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Default Bootstrap Helper (Org & User)
# ------------------------------------------------------------------------------

def _ensure_default_org_and_user(db: Session) -> tuple[str, str]:
    org = db.query(OrganizationModel).first()
    if not org:
        org = OrganizationModel(
            id=str(uuid.uuid4()),
            name="Default Studio Org",
            slug="default-studio",
        )
        db.add(org)
        db.flush()

    user = db.query(UserModel).filter_by(organization_id=org.id).first()
    if not user:
        user = UserModel(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            email="director@tattvaco.com",
            full_name="Lead Film Director",
            role="director",
        )
        db.add(user)
        db.commit()

    return org.id, user.id


# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------

@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Healthcheck verifying database connectivity."""
    db.execute(ProjectModel.__table__.select().limit(1))
    return {"status": "ok", "service": "tattva-api", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/v1/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(req: ProjectCreateRequest, db: Session = Depends(get_db)):
    default_org_id, default_user_id = _ensure_default_org_and_user(db)
    org_id = req.organization_id or default_org_id
    actor_id = req.actor_id or default_user_id

    project = ProjectModel(
        organization_id=org_id,
        title=req.title,
        logline=req.logline,
        genre=req.genre,
        status="active",
        current_version=1,
        created_by=actor_id,
    )
    db.add(project)
    db.flush()

    # Initial baseline version
    initial_version = ProjectVersionModel(
        project_id=project.id,
        version_number=1,
        branch_name="main",
        commit_message="Initial project baseline creation",
        committed_by=actor_id,
        snapshot_data={"title": project.title, "genre": project.genre},
    )
    db.add(initial_version)

    # Audit event
    audit = AuditEventModel(
        project_id=project.id,
        organization_id=org_id,
        actor_id=actor_id,
        action="project_created",
        target_type="project",
        target_id=project.id,
        details={"title": project.title},
    )
    db.add(audit)
    db.commit()
    db.refresh(project)
    return project


@app.get("/api/v1/projects", response_model=List[ProjectResponse])
def list_projects(
    organization_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ProjectModel)
    if organization_id:
        query = query.filter_by(organization_id=organization_id)
    return query.order_by(ProjectModel.created_at.desc()).all()


@app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(ProjectModel).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/api/v1/projects/{project_id}/assets/upload")
async def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
):
    project = db.query(ProjectModel).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    stored = storage.store_bytes(
        content=content,
        filename=file.filename or "script.fountain",
        project_id=project_id,
        organization_id=project.organization_id,
        mime_type=file.content_type,
    )

    asset = AssetModel(
        project_id=project_id,
        organization_id=project.organization_id,
        filename=stored.filename,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        storage_path=stored.storage_path,
        asset_type="script",
        is_original=True,
        uploaded_by=project.created_by,
        asset_metadata={"uploaded_filename": file.filename},
    )
    db.add(asset)
    db.flush()

    audit = AuditEventModel(
        project_id=project.id,
        organization_id=project.organization_id,
        actor_id=project.created_by,
        action="asset_uploaded",
        target_type="asset",
        target_id=asset.id,
        details={"filename": asset.filename, "checksum_sha256": asset.checksum_sha256},
    )
    db.add(audit)
    db.commit()

    return {
        "asset_id": asset.id,
        "filename": asset.filename,
        "size_bytes": asset.size_bytes,
        "checksum_sha256": asset.checksum_sha256,
        "storage_path": asset.storage_path,
    }


@app.get("/api/v1/projects/{project_id}/assets")
def list_assets(project_id: str, db: Session = Depends(get_db)):
    return db.query(AssetModel).filter_by(project_id=project_id).all()


@app.post("/api/v1/projects/{project_id}/workflows/script-intelligence")
def trigger_script_intelligence(
    project_id: str,
    req: WorkflowTriggerRequest,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
):
    project = db.query(ProjectModel).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    asset = db.query(AssetModel).filter_by(id=req.script_asset_id, project_id=project_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Script asset not found")

    actor_id = req.actor_id or project.created_by

    # Read raw script text from immutable storage
    raw_content = storage.get_bytes(asset.storage_path).decode("utf-8", errors="replace")

    # Create WorkflowRun row
    run = WorkflowRunModel(
        graph_id="script_intelligence",
        graph_version="1.0",
        project_id=project_id,
        organization_id=project.organization_id,
        actor_id=actor_id,
        expected_project_version=project.current_version,
        status="running",
        input_asset_ids=[asset.id],
    )
    db.add(run)
    db.commit()

    if req.sync_execution:
        # Run graph up to the approval interrupt node
        with get_checkpointer() as checkpointer:
            graph = build_script_intelligence_graph().compile(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": run.id}}
            initial_state = {
                "workflow_run_id": run.id,
                "project_id": project.id,
                "organization_id": project.organization_id,
                "actor_id": actor_id,
                "expected_project_version": project.current_version,
                "script_asset_id": asset.id,
                "raw_script_text": raw_content,
                "approval_status": "pending",
            }
            # Execute until interrupt
            result = graph.invoke(initial_state, config=config)

        db.commit()
        db.refresh(run)

        # Get generated approval request
        approval = db.query(ApprovalRequestModel).filter_by(
            workflow_run_id=run.id, status="pending"
        ).first()

        return {
            "workflow_run_id": run.id,
            "status": run.status,
            "approval_request_id": approval.id if approval else None,
            "candidate_summary": approval.candidate_summary if approval else {},
        }
    else:
        # Queue task into durable outbox
        outbox = OutboxTaskModel(
            workflow_run_id=run.id,
            task_type="script_intelligence",
            payload={
                "project_id": project_id,
                "script_asset_id": asset.id,
                "actor_id": actor_id,
            },
            status="pending",
        )
        db.add(outbox)
        db.commit()
        return {"workflow_run_id": run.id, "status": "queued"}


@app.get("/api/v1/projects/{project_id}/candidates")
def get_candidates(project_id: str, db: Session = Depends(get_db)):
    scenes = db.query(SceneCandidateModel).filter_by(project_id=project_id).all()
    entities = db.query(EntityCandidateModel).filter_by(project_id=project_id).all()
    approvals = db.query(ApprovalRequestModel).filter_by(project_id=project_id).all()
    return {
        "scenes": [
            {
                "id": s.id,
                "scene_number": s.scene_number,
                "heading": s.heading,
                "setting": s.setting,
                "location_name": s.location_name,
                "time_of_day": s.time_of_day,
                "summary": s.summary,
                "characters_present": s.characters_present,
                "status": s.status,
            }
            for s in scenes
        ],
        "entities": [
            {
                "id": e.id,
                "name": e.name,
                "category": e.category,
                "description": e.description,
                "confidence": e.confidence,
                "status": e.status,
            }
            for e in entities
        ],
        "approvals": [
            {
                "id": a.id,
                "workflow_run_id": a.workflow_run_id,
                "scope": a.scope,
                "status": a.status,
                "candidate_summary": a.candidate_summary,
            }
            for a in approvals
        ],
    }


@app.post("/api/v1/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    approval = db.query(ApprovalRequestModel).filter_by(id=approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval request already {approval.status}")

    # Resume the LangGraph workflow using the thread_id
    with get_checkpointer() as checkpointer:
        graph = build_script_intelligence_graph().compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": approval.workflow_run_id}}

        from langgraph.types import Command
        resume_command = Command(
            resume={
                "decision": req.decision,
                "notes": req.notes,
                "actor_id": req.actor_id,
                "approved_scene_ids": req.approved_scene_ids,
                "approved_entity_ids": req.approved_entity_ids,
            }
        )
        res = graph.invoke(resume_command, config=config)

    db.commit()

    project = db.query(ProjectModel).filter_by(id=approval.project_id).first()
    return {
        "status": "decision_applied",
        "approval_id": approval.id,
        "decision": req.decision,
        "new_project_version": project.current_version if project else None,
    }


@app.get("/api/v1/projects/{project_id}/scenes")
def get_canonical_scenes(project_id: str, db: Session = Depends(get_db)):
    return db.query(SceneModel).filter_by(project_id=project_id).order_by(SceneModel.scene_number.asc()).all()


@app.get("/api/v1/projects/{project_id}/entities")
def get_canonical_entities(project_id: str, db: Session = Depends(get_db)):
    return db.query(EntityModel).filter_by(project_id=project_id).order_by(EntityModel.category, EntityModel.name).all()


@app.get("/api/v1/projects/{project_id}/versions")
def get_project_versions(project_id: str, db: Session = Depends(get_db)):
    return db.query(ProjectVersionModel).filter_by(project_id=project_id).order_by(ProjectVersionModel.version_number.desc()).all()


@app.get("/api/v1/projects/{project_id}/audit-log")
def get_audit_log(project_id: str, db: Session = Depends(get_db)):
    return db.query(AuditEventModel).filter_by(project_id=project_id).order_by(AuditEventModel.created_at.desc()).all()
