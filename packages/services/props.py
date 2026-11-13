"""Props and weapons register, and per-scene prop holder tracking (D5, TFD-PRP-001/002).

No candidate/approval flow here (unlike costumes/locations) -- AT-PRP-001.1 describes a
direct save, not a versioned profile; the same direct-write pattern `FilmBibleRuleModel`
already uses for manually-proposed visual rules.
"""

from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from packages.domain.enums import AuditAction, PropKind
from packages.domain.errors import ValidationFailure
from packages.persistence.models import PropModel, PropStateModel
from packages.persistence.repositories import (
    AuditRepository,
    CharacterRepository,
    ProjectRepository,
    PropRepository,
    PropStateRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext

_VALID_KINDS = {k.value for k in PropKind}


class PropService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.props = PropRepository(db)
        self.prop_states = PropStateRepository(db)
        self.characters = CharacterRepository(db)
        self.authz = AuthzService(db)
        self.audit = AuditRepository(db)

    def create_prop(
        self,
        actor: ActorContext,
        project_id: str,
        *,
        name: str,
        kind: str,
        prop_type: str | None = None,
        design: str | None = None,
        material: str | None = None,
        scale: str | None = None,
        owner_character_id: str | None = None,
    ) -> PropModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        if kind not in _VALID_KINDS:
            # AT-PRP-001.1: any kind other than prop|weapon returns 422.
            raise ValidationFailure(f"Invalid prop kind '{kind}'; must be one of {sorted(_VALID_KINDS)}.")
        if not name.strip():
            raise ValidationFailure("name is required.")
        if owner_character_id is not None:
            self.characters.get_scoped(owner_character_id, project.id)

        prop = self.props.add(
            PropModel(
                project_id=project.id,
                organization_id=project.organization_id,
                name=name.strip(),
                kind=kind,
                type=prop_type,
                design=design,
                material=material,
                scale=scale,
                owner_character_id=owner_character_id,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.PROP_CREATED,
            target_type="prop",
            target_id=prop.id,
            details={"name": prop.name, "kind": kind},
        )
        self.db.commit()
        return prop

    def list_props(self, actor: ActorContext, project_id: str) -> List[PropModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.props.list_for_project(project.id)

    def create_state(
        self, actor: ActorContext, project_id: str, prop_id: str, *, scene_id: str, holder_character_id: str | None, notes: str | None = None
    ) -> PropStateModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        prop = self.props.get_scoped(prop_id, project.id)
        if holder_character_id is not None:
            self.characters.get_scoped(holder_character_id, project.id)

        state = self.prop_states.add(
            PropStateModel(
                prop_id=prop.id,
                project_id=project.id,
                organization_id=project.organization_id,
                scene_id=scene_id,
                holder_character_id=holder_character_id,
                notes=notes,
                created_by=actor.user_id,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.PROP_STATE_CREATED,
            target_type="prop",
            target_id=prop.id,
            details={"scene_id": scene_id, "holder_character_id": holder_character_id},
        )
        self.db.commit()
        return state

    def list_states(self, actor: ActorContext, project_id: str, prop_id: str) -> List[PropStateModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        self.props.get_scoped(prop_id, project.id)
        return self.prop_states.list_for_prop(prop_id)
