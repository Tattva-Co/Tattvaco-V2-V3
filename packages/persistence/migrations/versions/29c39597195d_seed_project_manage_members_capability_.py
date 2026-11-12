"""seed project.manage_members capability and grant D1 role templates

Revision ID: 29c39597195d
Revises: 63e256a9e65a
Create Date: 2026-11-11 14:36:19.507551+00:00

D1 (S-TEAM-02, TFD-IAM-003/004/005): packages.domain.capabilities.CAPABILITIES gained
'project.manage_members' (project member/role management), granted to the
'project_owner' and 'management' role templates. The static `capabilities` reference
table and every existing organization's role_template_capabilities rows were seeded by
an earlier migration (dd30049081b6) and do not pick up a code-level catalogue change on
their own, so this migration inserts the new capability row and grants it exactly like
dd30049081b6 and a9fb5bf54591 did for their own new capabilities/templates. Future
organizations get it automatically from RoleTemplateRepository.seed_defaults_for_org,
which reads the same (now-updated) DEFAULT_ROLE_TEMPLATES dict this migration does.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29c39597195d'
down_revision: Union[str, Sequence[str], None] = '63e256a9e65a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CAPABILITY_KEY = "project.manage_members"
_GRANTED_TO = ("project_owner", "management")


def upgrade() -> None:
    from packages.domain.capabilities import CAPABILITIES

    bind = op.get_bind()
    description = next(c.description for c in CAPABILITIES if c.key == _CAPABILITY_KEY)

    bind.execute(
        sa.text("INSERT INTO capabilities (key, description) VALUES (:key, :description)"),
        {"key": _CAPABILITY_KEY, "description": description},
    )

    templates = list(
        bind.execute(
            sa.text(
                "SELECT id FROM role_templates WHERE key = ANY(:keys)"
            ),
            {"keys": list(_GRANTED_TO)},
        )
    )
    for (template_id,) in templates:
        bind.execute(
            sa.text(
                "INSERT INTO role_template_capabilities (role_template_id, capability_key) "
                "VALUES (:template_id, :capability_key)"
            ),
            {"template_id": template_id, "capability_key": _CAPABILITY_KEY},
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM role_template_capabilities WHERE capability_key = :key"),
        {"key": _CAPABILITY_KEY},
    )
    bind.execute(sa.text("DELETE FROM capabilities WHERE key = :key"), {"key": _CAPABILITY_KEY})
