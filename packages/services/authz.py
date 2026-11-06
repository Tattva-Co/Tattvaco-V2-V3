"""Authorization (ADR-003 §2): who may do what, on which project.

Authentication (packages/services/auth.py, identity.py) answers "who is calling?".
This module answers "is that caller allowed to do this?" and is deliberately a separate
concern: every ``ActorContext`` that reaches a service has already been verified, but
until this module's checks are called, the service has no idea whether the actor holds
the right to perform the specific action it is about to take.

Enforcement lives here and is called from services, not routers (ADR-003 §2: "Enforcement
is in services, not routers"), because the service already has (or is about to look up)
the project and knows precisely which operation is being attempted; a router-level
dependency would have to duplicate that knowledge from the path alone.

Resolution order for ``require(actor, capability, project)``:
  1. The actor's org membership must be active, or access is denied outright (this also
     catches a user who was removed from the org since their token was issued).
  2. An org ``owner`` bypasses project_memberships entirely: a project cannot be fenced
     off from the organization that owns it.
  3. Otherwise, the actor needs an explicit ``project_memberships`` row for this project,
     whose role_template includes the required capability.
There is no "project exists, actor is an org member, so allow by default" fallback: that
was today's actual (undocumented) behaviour, and ADR-003 replaces it deliberately. The
migration backfills an explicit project_membership for every (existing user, existing
project) pair so no current user loses access (see migration
f3a7c9e1d5b0_add_authorization_tables.py).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from packages.domain.errors import TenantAccessViolation
from packages.persistence.models import ProjectModel
from packages.persistence.repositories import (
    MembershipRepository,
    ProjectMembershipRepository,
    RoleTemplateRepository,
)
from packages.services.identity import ActorContext


class AuthzService:
    def __init__(self, db: Session):
        self.db = db
        self.memberships = MembershipRepository(db)
        self.role_templates = RoleTemplateRepository(db)
        self.project_memberships = ProjectMembershipRepository(db)

    def require_org_member(self, actor: ActorContext) -> None:
        """The baseline check for an org-level action that doesn't target a project yet
        (today, just project creation). Raises TenantAccessViolation if the actor's
        membership is missing or suspended."""
        if not self.memberships.is_active_member(actor.user_id, actor.org_id):
            raise TenantAccessViolation("Your organization membership is not active.")

    def require(self, actor: ActorContext, capability: str, project: ProjectModel) -> None:
        """Raise TenantAccessViolation unless ``actor`` holds ``capability`` on ``project``.

        ``project`` must already have been fetched with ``ProjectRepository.get_scoped``
        (or equivalent), i.e. the caller has already established that the project exists
        and belongs to the actor's organization -- this method only adds the finer,
        role-based check on top of that tenant boundary; it never widens access across
        organizations.
        """
        if not self.memberships.is_active_member(actor.user_id, actor.org_id):
            raise TenantAccessViolation("Your organization membership is not active.")
        if self.memberships.is_owner(actor.user_id, actor.org_id):
            return

        membership = self.project_memberships.get_for_user_project(actor.user_id, project.id)
        if membership is None:
            raise TenantAccessViolation(f"You have no role on project '{project.id}'.")
        if capability not in self.role_templates.capabilities_for(membership.role_template_id):
            raise TenantAccessViolation(f"Your role does not grant '{capability}' on this project.")
