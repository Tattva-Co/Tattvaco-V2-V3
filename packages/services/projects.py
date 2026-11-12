"""Project lifecycle and read models for the project workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from packages.domain.enums import AuditAction, ProductionMode, ProjectStatus
from packages.domain.errors import InvalidStateError, NotFoundError, TenantAccessViolation, ValidationFailure
from packages.domain.format_templates import FORMAT_TEMPLATES_BY_KEY
from packages.persistence.models import (
    ApprovalRequestModel,
    AuditEventModel,
    EntityCandidateModel,
    EntityModel,
    EpisodeModel,
    FilmBibleRuleCandidateModel,
    OutputProfileModel,
    ProjectMembershipModel,
    ProjectModel,
    ProjectVersionModel,
    ResearchClaimCandidateModel,
    ResearchQuestionCandidateModel,
    SceneCandidateModel,
    SceneModel,
    StoryboardPanelCandidateModel,
)
from packages.persistence.repositories import (
    ApprovalRepository,
    AuditRepository,
    CandidateRepository,
    CanonicalRepository,
    EpisodeRepository,
    OutputProfileRepository,
    ProjectMembershipRepository,
    ProjectRepository,
    RoleTemplateRepository,
    UserRepository,
    WorkflowRunRepository,
)
from packages.services.authz import AuthzService
from packages.services.identity import ActorContext

#: Removing the last project member holding this capability is blocked (TFD-IAM-005,
#: AT-TEAM-02.1). The acceptance criterion says "once a screenplay is locked", but
#: screenplay locking (D2) doesn't exist yet -- enforcing it unconditionally now is
#: strictly more conservative and already satisfies the rule once D2 lands.
_GUARANTEED_CAPABILITY = "screenplay.approve_lock"


@dataclass
class CandidateOverview:
    scenes: List[SceneCandidateModel]
    entities: List[EntityCandidateModel]
    research_claims: List[ResearchClaimCandidateModel]
    research_questions: List[ResearchQuestionCandidateModel]
    storyboard_panels: List[StoryboardPanelCandidateModel]
    film_bible_rules: List[FilmBibleRuleCandidateModel]
    approvals: List[ApprovalRequestModel]


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.project_memberships = ProjectMembershipRepository(db)
        self.role_templates = RoleTemplateRepository(db)
        self.output_profiles = OutputProfileRepository(db)
        self.episodes = EpisodeRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)
        self.authz = AuthzService(db)

    def create(
        self,
        actor: ActorContext,
        *,
        title: str,
        logline: str | None = None,
        genre: str | None = None,
        production_mode: str | None = None,
        format_template_key: str | None = None,
        quality_profile: str | None = None,
        scale: str | None = None,
    ) -> ProjectModel:
        # project.create has no project to scope the check to yet; any active member of
        # the organization may create a project (ADR-003 §2).
        self.authz.require_org_member(actor)
        if format_template_key is not None and format_template_key not in FORMAT_TEMPLATES_BY_KEY:
            raise ValidationFailure(f"Unknown format_template_key '{format_template_key}'.")
        # AT-PRJ-001.3: the legacy {title, logline, genre} body (no mode given) defaults
        # to "mixed", not the DB column's "fully_ai" migration-backfill default
        # (DEC-021, which applies only to rows that predate this field being settable).
        effective_mode = production_mode or ProductionMode.MIXED.value
        project = self.projects.add(
            ProjectModel(
                organization_id=actor.org_id,
                title=title,
                logline=logline,
                genre=genre,
                status=ProjectStatus.ACTIVE.value,
                production_mode=effective_mode,
                format_template_key=format_template_key,
                quality_profile=quality_profile,
                scale=scale,
                current_version=1,
                created_by=actor.user_id,
            )
        )
        self.db.flush()
        # Grant the creator the project_owner role on their own new project. An org owner
        # wouldn't need this (AuthzService bypasses project_memberships for owners), but a
        # plain 'member' creating their first project otherwise couldn't act on it at all
        # -- there is no separate "invite yourself" step. 'project_owner' (not 'director')
        # specifically: JRN-01 (Guided Workspace section 1, which every project must pass
        # before anything else unlocks) is act_capability=project.admin throughout, which
        # 'director' does not grant -- a creator holding only 'director' could create a
        # project and then never be able to complete its own setup.
        owner_template = self.role_templates.get_by_key(actor.org_id, "project_owner")
        if owner_template is not None:
            self.project_memberships.add(
                ProjectMembershipModel(
                    user_id=actor.user_id, project_id=project.id, role_template_id=owner_template.id
                )
            )
        self.projects.add_version(
            ProjectVersionModel(
                project_id=project.id,
                organization_id=project.organization_id,
                version_number=1,
                branch_name="main",
                commit_message="Initial project baseline creation",
                committed_by=actor.user_id,
                snapshot_data={"title": title, "logline": logline, "genre": genre},
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=actor.org_id,
            actor_id=actor.user_id,
            action=AuditAction.PROJECT_CREATED,
            target_type="project",
            target_id=project.id,
            details={"title": title},
        )
        self.db.commit()
        self.db.refresh(project)
        return project

    def list(self, actor: ActorContext, *, include_archived: bool = False) -> List[ProjectModel]:
        """TFD-PRJ-002, AT-PRJ-002.1: an org owner sees every project in the org; any
        other member sees only the projects they hold an explicit project_membership
        on, never the whole org's project list."""
        if self.authz.memberships.is_owner(actor.user_id, actor.org_id):
            return self.projects.list_for_org(actor.org_id, include_archived=include_archived)
        project_ids = self.project_memberships.list_project_ids_for_user(actor.user_id)
        return self.projects.list_for_org(actor.org_id, project_ids=project_ids, include_archived=include_archived)

    def get(self, actor: ActorContext, project_id: str) -> ProjectModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        # AT-PRJ-002.1: a project the actor has no standing relationship to (not its
        # org's owner, no project_membership row) reads as 404, not 403 -- its
        # existence is not revealed to a caller outside it. project.read is granted by
        # every role template, so the only way an actual member could fail the
        # authz.require below is the capability check itself, which still 403s.
        if not self.authz.memberships.is_active_member(actor.user_id, actor.org_id):
            raise TenantAccessViolation("Your organization membership is not active.")
        if not self.authz.memberships.is_owner(actor.user_id, actor.org_id):
            if self.project_memberships.get_for_user_project(actor.user_id, project_id) is None:
                raise NotFoundError(f"Project '{project_id}' not found.")
        self.authz.require(actor, "project.read", project)
        return project

    def update(self, actor: ActorContext, project_id: str, **fields: Any) -> ProjectModel:
        """PATCH semantics: only keys actually present in ``fields`` are changed."""
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.admin", project)

        if "format_template_key" in fields and fields["format_template_key"] is not None:
            if fields["format_template_key"] not in FORMAT_TEMPLATES_BY_KEY:
                raise ValidationFailure(f"Unknown format_template_key '{fields['format_template_key']}'.")

        before: dict[str, Any] = {}
        after: dict[str, Any] = {}
        for key, value in fields.items():
            if not hasattr(project, key):
                continue
            current = getattr(project, key)
            if current == value:
                continue
            before[key] = current
            after[key] = value
            setattr(project, key, value)

        if after:
            self.audit.record(
                project_id=project.id,
                organization_id=project.organization_id,
                actor_id=actor.user_id,
                action=AuditAction.PROJECT_UPDATED,
                target_type="project",
                target_id=project.id,
                details={"before": before, "after": after},
            )
        self.db.commit()
        self.db.refresh(project)
        return project

    def archive(self, actor: ActorContext, project_id: str) -> ProjectModel:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.admin", project)
        project.status = ProjectStatus.ARCHIVED.value
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.PROJECT_ARCHIVED,
            target_type="project",
            target_id=project.id,
            details={},
        )
        self.db.commit()
        self.db.refresh(project)
        return project

    def unarchive(self, actor: ActorContext, project_id: str) -> ProjectModel:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.admin", project)
        project.status = ProjectStatus.ACTIVE.value
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.PROJECT_UNARCHIVED,
            target_type="project",
            target_id=project.id,
            details={},
        )
        self.db.commit()
        self.db.refresh(project)
        return project

    def versions(self, actor: ActorContext, project_id: str) -> List[ProjectVersionModel]:
        self.get(actor, project_id)
        return self.projects.list_versions(project_id)

    def audit_log(self, actor: ActorContext, project_id: str) -> List[AuditEventModel]:
        project = self.get(actor, project_id)
        self.authz.require(actor, "audit.read", project)
        return self.audit.list_for_project(project_id)

    def canonical_scenes(self, actor: ActorContext, project_id: str) -> List[SceneModel]:
        self.get(actor, project_id)
        return CanonicalRepository(self.db).scenes_for_project(project_id)

    def canonical_entities(self, actor: ActorContext, project_id: str) -> List[EntityModel]:
        self.get(actor, project_id)
        return CanonicalRepository(self.db).entities_for_project(project_id)

    def candidates(self, actor: ActorContext, project_id: str) -> CandidateOverview:
        self.get(actor, project_id)
        candidates = CandidateRepository(self.db)
        return CandidateOverview(
            scenes=candidates.scenes_for_project(project_id),
            entities=candidates.entities_for_project(project_id),
            research_claims=candidates.claims_for_project(project_id),
            research_questions=candidates.questions_for_project(project_id),
            storyboard_panels=candidates.storyboard_panels_for_project(project_id),
            film_bible_rules=candidates.film_bible_rules_for_project(project_id),
            approvals=ApprovalRepository(self.db).list_for_project(project_id),
        )

    # -- Output profiles (D1, TFD-FMT-002) ------------------------------------

    def list_output_profiles(self, actor: ActorContext, project_id: str) -> List[OutputProfileModel]:
        self.get(actor, project_id)
        return self.output_profiles.list_for_project(project_id)

    def create_output_profile(self, actor: ActorContext, project_id: str, **fields: Any) -> OutputProfileModel:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.admin", project)
        profile = self.output_profiles.add(
            OutputProfileModel(project_id=project.id, organization_id=project.organization_id, **fields)
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.OUTPUT_PROFILE_CREATED,
            target_type="output_profile",
            target_id=profile.id,
            details={"name": profile.name},
        )
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_output_profile(
        self, actor: ActorContext, project_id: str, profile_id: str, **fields: Any
    ) -> OutputProfileModel:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.admin", project)
        profile = self.output_profiles.get_scoped(profile_id, project_id)
        for key, value in fields.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.OUTPUT_PROFILE_UPDATED,
            target_type="output_profile",
            target_id=profile.id,
            details={"fields": list(fields.keys())},
        )
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete_output_profile(self, actor: ActorContext, project_id: str, profile_id: str) -> None:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.admin", project)
        profile = self.output_profiles.get_scoped(profile_id, project_id)
        self.output_profiles.delete(profile)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.OUTPUT_PROFILE_DELETED,
            target_type="output_profile",
            target_id=profile_id,
            details={"name": profile.name},
        )
        self.db.commit()

    # -- Episodes (D1, TFD-FMT-003) -------------------------------------------

    def list_episodes(self, actor: ActorContext, project_id: str) -> List[EpisodeModel]:
        self.get(actor, project_id)
        return self.episodes.list_for_project(project_id)

    def create_episode(
        self, actor: ActorContext, project_id: str, *, episode_number: int, title: str | None = None
    ) -> EpisodeModel:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.admin", project)
        if any(e.episode_number == episode_number for e in self.episodes.list_for_project(project_id)):
            raise InvalidStateError(f"Episode {episode_number} already exists for this project.")
        episode = self.episodes.add(
            EpisodeModel(
                project_id=project.id,
                organization_id=project.organization_id,
                episode_number=episode_number,
                title=title,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.EPISODE_CREATED,
            target_type="episode",
            target_id=episode.id,
            details={"episode_number": episode_number, "title": title},
        )
        self.db.commit()
        self.db.refresh(episode)
        return episode

    # -- Members & roles (D1, S-TEAM-02) --------------------------------------

    def list_role_templates(self, actor: ActorContext, project_id: str) -> List[Dict[str, Any]]:
        """Every role template assignable on this project (S-TEAM-02's role picker) --
        scoped to the actor's own org, not hardcoded client-side, so a future
        org-customized template shows up automatically."""
        self.get(actor, project_id)
        return [
            {"key": t.key, "name": t.name, "capabilities": sorted(self.role_templates.capabilities_for(t.id))}
            for t in self.role_templates.list_for_org(actor.org_id)
        ]

    def list_members(self, actor: ActorContext, project_id: str) -> List[Dict[str, Any]]:
        self.get(actor, project_id)
        rows = []
        for membership in self.project_memberships.list_for_project(project_id):
            user = self.users.get(membership.user_id)
            template = self.role_templates.get_scoped(membership.role_template_id, actor.org_id)
            rows.append(
                {
                    "user_id": membership.user_id,
                    "email": user.email if user else "unknown",
                    "full_name": user.full_name if user else "unknown",
                    "role_template_key": template.key,
                    "role_template_name": template.name,
                    "capabilities": sorted(self.role_templates.capabilities_for(template.id)),
                }
            )
        return rows

    def add_member(
        self, actor: ActorContext, project_id: str, *, email: str, role_template_key: str
    ) -> dict[str, Any]:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.manage_members", project)

        target_user = self.users.get_by_email_in_org(email, actor.org_id)
        if target_user is None or not self.authz.memberships.is_active_member(target_user.id, actor.org_id):
            raise ValidationFailure(f"'{email}' is not an active member of this organization.")
        template = self.role_templates.get_by_key(actor.org_id, role_template_key)
        if template is None:
            raise ValidationFailure(f"Unknown role_template_key '{role_template_key}'.")

        existing = self.project_memberships.get_for_user_project(target_user.id, project_id)
        if existing is not None:
            raise InvalidStateError(f"'{email}' is already a member of this project.")

        membership = self.project_memberships.add(
            ProjectMembershipModel(user_id=target_user.id, project_id=project_id, role_template_id=template.id)
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.PROJECT_MEMBER_ADDED,
            target_type="project_membership",
            target_id=membership.id,
            details={"user_id": target_user.id, "email": email, "role_template_key": role_template_key},
        )
        self.db.commit()
        return self._member_row(target_user, template)

    def update_member_role(
        self, actor: ActorContext, project_id: str, user_id: str, *, role_template_key: str
    ) -> dict[str, Any]:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.manage_members", project)

        membership = self.project_memberships.get_for_user_project(user_id, project_id)
        if membership is None:
            raise NotFoundError(f"User '{user_id}' is not a member of this project.")
        new_template = self.role_templates.get_by_key(actor.org_id, role_template_key)
        if new_template is None:
            raise ValidationFailure(f"Unknown role_template_key '{role_template_key}'.")

        if _GUARANTEED_CAPABILITY in self.role_templates.capabilities_for(membership.role_template_id):
            if _GUARANTEED_CAPABILITY not in self.role_templates.capabilities_for(new_template.id):
                self._assert_not_last_holder(project_id, user_id)

        before_key = self.role_templates.get_scoped(membership.role_template_id, actor.org_id).key
        membership.role_template_id = new_template.id
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.PROJECT_MEMBER_ROLE_CHANGED,
            target_type="project_membership",
            target_id=membership.id,
            details={"user_id": user_id, "before": before_key, "after": role_template_key},
        )
        self.db.commit()
        target_user = self.users.get(user_id)
        return self._member_row(target_user, new_template)

    def remove_member(self, actor: ActorContext, project_id: str, user_id: str) -> None:
        project = self.get(actor, project_id)
        self.authz.require(actor, "project.manage_members", project)

        membership = self.project_memberships.get_for_user_project(user_id, project_id)
        if membership is None:
            raise NotFoundError(f"User '{user_id}' is not a member of this project.")
        if _GUARANTEED_CAPABILITY in self.role_templates.capabilities_for(membership.role_template_id):
            self._assert_not_last_holder(project_id, user_id)

        self.project_memberships.delete(membership)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.PROJECT_MEMBER_REMOVED,
            target_type="project_membership",
            target_id=membership.id,
            details={"user_id": user_id},
        )
        self.db.commit()

    def _assert_not_last_holder(self, project_id: str, excluding_user_id: str) -> None:
        """AT-TEAM-02.1: the project must keep at least one holder of
        ``_GUARANTEED_CAPABILITY`` other than the member being removed/demoted."""
        for membership in self.project_memberships.list_for_project(project_id):
            if membership.user_id == excluding_user_id:
                continue
            if _GUARANTEED_CAPABILITY in self.role_templates.capabilities_for(membership.role_template_id):
                return
        raise InvalidStateError(
            f"Cannot remove the project's only '{_GUARANTEED_CAPABILITY}' holder."
        )

    def _member_row(self, user, template) -> Dict[str, Any]:
        return {
            "user_id": user.id if user else "",
            "email": user.email if user else "unknown",
            "full_name": user.full_name if user else "unknown",
            "role_template_key": template.key,
            "role_template_name": template.name,
            "capabilities": sorted(self.role_templates.capabilities_for(template.id)),
        }

    # -- Project Overview summary (D1, TFD-PRJ-007) ---------------------------

    def summary(self, actor: ActorContext, project_id: str) -> dict[str, Any]:
        project = self.get(actor, project_id)

        scenes = CanonicalRepository(self.db).scenes_for_project(project_id)
        mode_counts: dict[str, int] = {}
        for scene in scenes:
            effective = scene.production_mode or project.production_mode
            mode_counts[effective] = mode_counts.get(effective, 0) + 1

        pending_approvals = [
            a for a in ApprovalRepository(self.db).list_for_project(project_id) if a.status == "pending"
        ]
        running_tasks = WorkflowRunRepository(self.db).list_for_project(
            project_id, statuses=("queued", "running", "awaiting_approval")
        )
        recent_changes = self.audit.list_for_project(project_id)[:10]

        from packages.services.journey import JourneyService

        sections = JourneyService(self.db).get_journey(actor, project_id)
        next_action = _derive_next_action(sections)

        return {
            "project_id": project.id,
            "project_version": project.current_version,
            "canonical_screenplay_version": None,
            "screenplay_lock_state": "none_locked",
            "scene_count_by_effective_mode": mode_counts,
            "pending_approvals_count": len(pending_approvals),
            "unresolved_high_severity_findings_count": 0,
            "running_tasks": [
                {
                    "workflow_run_id": r.id,
                    "graph_id": r.graph_id,
                    "status": r.status,
                    "created_at": r.created_at,
                }
                for r in running_tasks
            ],
            "recent_changes": [
                {
                    "action": c.action,
                    "actor_id": c.actor_id,
                    "target_type": c.target_type,
                    "target_id": c.target_id,
                    "created_at": c.created_at,
                }
                for c in recent_changes
            ],
            "next_action": next_action,
        }


def _derive_next_action(sections: list) -> dict[str, Any] | None:
    """The first incomplete, applicable section's first incomplete required group --
    or, if a section has no single actionable group, a generic "continue this
    section" recommendation. Never fabricated: derived purely from the journey
    engine's own stored status (S-PRJ-01 AC #1)."""
    for section_view in sections:
        if section_view.status in ("completed", "ready_to_continue"):
            continue
        for group_view in section_view.groups:
            if not group_view.applies:
                continue
            if group_view.group.required and group_view.status not in ("completed", "not_applicable"):
                return {
                    "jrn_id": group_view.group.id,
                    "title": group_view.group.title,
                    "reason": f"Required to complete {section_view.section.title}",
                }
        return {
            "jrn_id": section_view.section.id,
            "title": section_view.section.title,
            "reason": "Continue this section",
        }
    return None
