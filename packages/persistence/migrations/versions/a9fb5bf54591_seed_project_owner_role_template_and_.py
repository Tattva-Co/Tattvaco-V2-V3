"""seed project_owner role template and backfill project creators

Revision ID: a9fb5bf54591
Revises: 5915e59b2818
Create Date: 2026-11-07 17:18:10.504041+00:00

Fixes a real gap found while building the GW2 frontend: ``ProjectService.create`` (see
packages/services/projects.py) auto-grants a project's creator the 'director' role
template so a plain org 'member' can act on the project they just made. But every group
in JRN-01 (Guided Workspace section 1 -- "Project Workspace & Setup", which gates every
other section) has ``act_capability: project.admin``, which 'director' does not include.
A solo creator who is not also their organization's owner could create a project and
then never be able to complete its own required first section.

This migration:

  1. Adds no new capabilities (packages.domain.capabilities.CAPABILITIES is unchanged --
     'project_owner' is a new bundle of existing capability keys, everything except
     'project.create', which is org-level and not tied to any one project).
  2. Seeds a 'project_owner' role_template + its role_template_capabilities rows for every
     EXISTING organization (future organizations get it from
     RoleTemplateRepository.seed_defaults_for_org, which reads the same
     DEFAULT_ROLE_TEMPLATES dict this migration does). Idempotent by (org, key), like the
     RBAC migration (dd30049081b6) this follows the same pattern as.
  3. Backfills existing data: for every project, if its creator's OWN project_membership
     row currently points at that org's 'director' template, it is retargeted to
     'project_owner' instead. This touches only the creator's own row -- a 'director' row
     some other project member was deliberately assigned by a project admin is untouched,
     since it is keyed on (project.created_by = project_memberships.user_id), not on
     everyone who happens to hold 'director'.

Additive and narrowly-scoped: no column, table or unrelated row is altered.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9fb5bf54591'
down_revision: Union[str, Sequence[str], None] = '5915e59b2818'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROLE_KEY = "project_owner"


def upgrade() -> None:
    import uuid
    from datetime import datetime, timezone

    from packages.domain.capabilities import DEFAULT_ROLE_TEMPLATES

    capability_keys = DEFAULT_ROLE_TEMPLATES[_ROLE_KEY]
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    org_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM organizations"))]
    project_owner_template_id_by_org: dict[str, str] = {}
    director_template_id_by_org: dict[str, str] = {}

    for org_id in org_ids:
        director_row = bind.execute(
            sa.text("SELECT id FROM role_templates WHERE organization_id = :org_id AND key = 'director'"),
            {"org_id": org_id},
        ).first()
        if director_row is not None:
            director_template_id_by_org[org_id] = director_row[0]

        existing = bind.execute(
            sa.text("SELECT id FROM role_templates WHERE organization_id = :org_id AND key = :key"),
            {"org_id": org_id, "key": _ROLE_KEY},
        ).first()
        if existing is not None:
            project_owner_template_id_by_org[org_id] = existing[0]
            continue

        template_id = str(uuid.uuid4())
        project_owner_template_id_by_org[org_id] = template_id
        bind.execute(
            sa.text(
                "INSERT INTO role_templates (id, organization_id, key, name, is_system, created_at) "
                "VALUES (:id, :org_id, :key, :name, true, :now)"
            ),
            {"id": template_id, "org_id": org_id, "key": _ROLE_KEY, "name": _ROLE_KEY.replace("_", " ").title(), "now": now},
        )
        for capability_key in capability_keys:
            bind.execute(
                sa.text(
                    "INSERT INTO role_template_capabilities (role_template_id, capability_key) "
                    "VALUES (:template_id, :capability_key)"
                ),
                {"template_id": template_id, "capability_key": capability_key},
            )

    # Backfill: retarget each project creator's own 'director' project_membership row
    # (if they have one) to this org's new 'project_owner' template.
    projects = list(bind.execute(sa.text("SELECT id, organization_id, created_by FROM projects")))
    for project_id, organization_id, created_by in projects:
        director_template_id = director_template_id_by_org.get(organization_id)
        project_owner_template_id = project_owner_template_id_by_org.get(organization_id)
        if director_template_id is None or project_owner_template_id is None:
            continue
        bind.execute(
            sa.text(
                "UPDATE project_memberships SET role_template_id = :project_owner_id "
                "WHERE project_id = :project_id AND user_id = :created_by AND role_template_id = :director_id"
            ),
            {
                "project_owner_id": project_owner_template_id,
                "project_id": project_id,
                "created_by": created_by,
                "director_id": director_template_id,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()

    project_owner_templates = list(
        bind.execute(sa.text("SELECT id, organization_id FROM role_templates WHERE key = :key"), {"key": _ROLE_KEY})
    )

    for template_id, organization_id in project_owner_templates:
        director_row = bind.execute(
            sa.text("SELECT id FROM role_templates WHERE organization_id = :org_id AND key = 'director'"),
            {"org_id": organization_id},
        ).first()
        if director_row is not None:
            # Point any project_memberships this migration retargeted back at 'director'
            # so the table is never left referencing a role_template about to be deleted.
            bind.execute(
                sa.text(
                    "UPDATE project_memberships SET role_template_id = :director_id "
                    "WHERE role_template_id = :project_owner_id"
                ),
                {"director_id": director_row[0], "project_owner_id": template_id},
            )
        bind.execute(
            sa.text("DELETE FROM role_template_capabilities WHERE role_template_id = :template_id"),
            {"template_id": template_id},
        )
        bind.execute(sa.text("DELETE FROM role_templates WHERE id = :template_id"), {"template_id": template_id})
