"""seed screenplay.propose_revision capability

Revision ID: 910fdd9ce4ec
Revises: 74e3d4a1909a
Create Date: 2026-11-12 08:02:22.475095+00:00

D2 (S-SCR-03, TFD-SCR-006): packages.domain.capabilities.CAPABILITIES gained
'screenplay.propose_revision' (create/edit a director-led screenplay revision),
granted to the 'director' and 'project_owner' role templates. Same pattern as
29c39597195d (D1's project.manage_members): seed the new row in the static
`capabilities` reference table and grant it to every existing organization's matching
role_templates, since that seeding only happens automatically for organizations
created after this migration (RoleTemplateRepository.seed_defaults_for_org).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '910fdd9ce4ec'
down_revision: Union[str, Sequence[str], None] = '74e3d4a1909a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CAPABILITY_KEY = "screenplay.propose_revision"
_GRANTED_TO = ("project_owner", "director")


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
            sa.text("SELECT id FROM role_templates WHERE key = ANY(:keys)"),
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
