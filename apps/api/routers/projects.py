"""Project workspace endpoints: projects, versions, audit log, canonical film bible."""

from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    AuditEventResponse,
    CandidatesResponse,
    EntityResponse,
    EpisodeCreateRequest,
    EpisodeResponse,
    OutputProfileCreateRequest,
    OutputProfileResponse,
    OutputProfileUpdateRequest,
    ProjectCreateRequest,
    ProjectMemberAddRequest,
    ProjectMemberResponse,
    ProjectMemberRoleUpdateRequest,
    ProjectResponse,
    ProjectSummaryResponse,
    ProjectUpdateRequest,
    ProjectVersionResponse,
    RoleTemplateResponse,
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
    return ProjectService(db).create(
        actor,
        title=req.title,
        logline=req.logline,
        genre=req.genre,
        production_mode=req.production_mode.value if req.production_mode else None,
        format_template_key=req.format_template_key,
        quality_profile=req.quality_profile.value if req.quality_profile else None,
        scale=req.scale.value if req.scale else None,
    )


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    include_archived: bool = False, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    return ProjectService(db).list(actor, include_archived=include_archived)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).get(actor, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    fields = req.model_dump(exclude_unset=True)
    for enum_field in ("production_mode", "quality_profile", "scale"):
        if enum_field in fields and fields[enum_field] is not None:
            fields[enum_field] = fields[enum_field].value if hasattr(fields[enum_field], "value") else fields[enum_field]
    return ProjectService(db).update(actor, project_id, **fields)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).archive(actor, project_id)


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
def unarchive_project(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).unarchive(actor, project_id)


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse)
def get_project_summary(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).summary(actor, project_id)


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
        scenes=overview.scenes,
        entities=overview.entities,
        research_claims=overview.research_claims,
        research_questions=overview.research_questions,
        storyboard_panels=overview.storyboard_panels,
        film_bible_rules=overview.film_bible_rules,
        approvals=overview.approvals,
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


# -- Output profiles (D1, TFD-FMT-002) ---------------------------------------


@router.get("/{project_id}/output-profiles", response_model=List[OutputProfileResponse])
def list_output_profiles(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).list_output_profiles(actor, project_id)


@router.post(
    "/{project_id}/output-profiles", response_model=OutputProfileResponse, status_code=status.HTTP_201_CREATED
)
def create_output_profile(
    project_id: str,
    req: OutputProfileCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ProjectService(db).create_output_profile(actor, project_id, **req.model_dump())


@router.patch("/{project_id}/output-profiles/{profile_id}", response_model=OutputProfileResponse)
def update_output_profile(
    project_id: str,
    profile_id: str,
    req: OutputProfileUpdateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ProjectService(db).update_output_profile(
        actor, project_id, profile_id, **req.model_dump(exclude_unset=True)
    )


@router.delete("/{project_id}/output-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_output_profile(
    project_id: str, profile_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    ProjectService(db).delete_output_profile(actor, project_id, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -- Episodes (D1, TFD-FMT-003) ----------------------------------------------


@router.get("/{project_id}/episodes", response_model=List[EpisodeResponse])
def list_episodes(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).list_episodes(actor, project_id)


@router.post("/{project_id}/episodes", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
def create_episode(
    project_id: str,
    req: EpisodeCreateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ProjectService(db).create_episode(actor, project_id, episode_number=req.episode_number, title=req.title)


# -- Members & roles (D1, S-TEAM-02) -----------------------------------------


@router.get("/{project_id}/role-templates", response_model=List[RoleTemplateResponse])
def list_role_templates(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).list_role_templates(actor, project_id)


@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
def list_members(project_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)):
    return ProjectService(db).list_members(actor, project_id)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: str,
    req: ProjectMemberAddRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ProjectService(db).add_member(actor, project_id, email=req.email, role_template_key=req.role_template_key)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def update_member_role(
    project_id: str,
    user_id: str,
    req: ProjectMemberRoleUpdateRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    return ProjectService(db).update_member_role(
        actor, project_id, user_id, role_template_key=req.role_template_key
    )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: str, user_id: str, actor: ActorContext = Depends(get_actor), db: Session = Depends(get_db)
):
    ProjectService(db).remove_member(actor, project_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
