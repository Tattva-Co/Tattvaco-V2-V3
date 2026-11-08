"""tenant_id_on_canon_tables_unique_version

Revision ID: ab1dac6edef2
Revises: a9fb5bf54591
Create Date: 2026-11-06 09:00:00+00:00

Closes the two C4/C5 leftovers (plan TFD-ENG-002 C4/C5 scope; TFD-IAM-009, TFD-VER-001):

1. ``organization_id`` on scenes, entities, scene_candidates, entity_candidates and
   project_versions, so every tenant-owned row carries its tenant directly instead of
   only through its project. Added expand -> backfill -> contract: nullable first,
   filled from the owning project, then NOT NULL with a foreign key and an index.

2. A unique ``(project_id, version_number)`` index on project_versions. C4's row lock
   prevents the race in application code; this makes a duplicate impossible in the
   database. The upgrade checks for existing duplicates first and stops with a clear
   message rather than deleting or renumbering anything.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab1dac6edef2'
down_revision: Union[str, Sequence[str], None] = 'a9fb5bf54591'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ('scenes', 'entities', 'scene_candidates', 'entity_candidates', 'project_versions')


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # 0. Pre-check: refuse to add the unique index over existing duplicates.
    duplicates = bind.execute(sa.text(
        "SELECT project_id, version_number, COUNT(*) AS n FROM project_versions "
        "GROUP BY project_id, version_number HAVING COUNT(*) > 1"
    )).fetchall()
    if duplicates:
        listed = ', '.join(f'{d.project_id} v{d.version_number} x{d.n}' for d in duplicates[:10])
        raise RuntimeError(
            f'project_versions has {len(duplicates)} duplicate (project_id, version_number) '
            f'pair(s): {listed}. Resolve them by hand before running this migration; '
            'it does not delete or renumber versions.'
        )

    for table in TABLES:
        # 1. Expand.
        op.add_column(table, sa.Column('organization_id', sa.String(length=36), nullable=True))
        # 2. Backfill from the owning project.
        op.execute(
            f"UPDATE {table} AS t SET organization_id = p.organization_id "
            f"FROM projects AS p WHERE t.project_id = p.id AND t.organization_id IS NULL"
        )
        # 3. Contract.
        op.alter_column(table, 'organization_id', nullable=False)
        op.create_foreign_key(f'fk_{table}_organization_id', table, 'organizations', ['organization_id'], ['id'])
        op.create_index(op.f(f'ix_{table}_organization_id'), table, ['organization_id'], unique=False)

    op.create_index('uq_project_versions_project_number', 'project_versions',
                    ['project_id', 'version_number'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_project_versions_project_number', table_name='project_versions')
    for table in reversed(TABLES):
        op.drop_index(op.f(f'ix_{table}_organization_id'), table_name=table)
        op.drop_constraint(f'fk_{table}_organization_id', table, type_='foreignkey')
        op.drop_column(table, 'organization_id')
