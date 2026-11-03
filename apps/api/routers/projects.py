"""Project workspace endpoints: projects, versions, audit log, canonical film bible."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    AuditEventResponse,
    CandidatesResponse,
    EntityResponse,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectVersionResponse,
    SceneResponse,
)
from packages.services.identity import ActorContext
from packages.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ProjectService(db).create(actor, title=req.title, logline=req.logline, genre=req.genre)


@router.get("", response_model=List[ProjectResponse])
def list_projects(actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).list(actor)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).get(actor, project_id)


@router.get("/{project_id}/versions", response_model=List[ProjectVersionResponse])
def get_project_versions(
    project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ProjectService(db).versions(actor, project_id)


@router.get("/{project_id}/audit-log", response_model=List[AuditEventResponse])
def get_audit_log(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).audit_log(actor, project_id)


@router.get("/{project_id}/candidates", response_model=CandidatesResponse)
def get_candidates(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    overview = ProjectService(db).candidates(actor, project_id)
    return CandidatesResponse(
        scenes=overview.scenes, entities=overview.entities, approvals=overview.approvals
    )


@router.get("/{project_id}/scenes", response_model=List[SceneResponse])
def get_canonical_scenes(
    project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ProjectService(db).canonical_scenes(actor, project_id)


@router.get("/{project_id}/entities", response_model=List[EntityResponse])
def get_canonical_entities(
    project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ProjectService(db).canonical_entities(actor, project_id)
