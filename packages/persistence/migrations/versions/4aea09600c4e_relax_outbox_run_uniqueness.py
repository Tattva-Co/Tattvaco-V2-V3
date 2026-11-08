"""relax_outbox_run_uniqueness

Revision ID: 4aea09600c4e
Revises: 02b6605b5488
Create Date: 2026-11-08 02:30:00+00:00

Closes the last C6 scope item (plan TFD-ENG-002 C6: "the outbox workflow_run_id
uniqueness constraint is relaxed (expand/contract)").

Before: outbox_tasks.workflow_run_id was unique, so a run could only ever have one
task, even after that task completed or was dead-lettered.
After: a run may have several tasks over time, but at most one active (pending or
claimed) task at a time, so the same run still can't be dispatched twice.

Expand -> contract: the partial unique index is created first, so there is never a
moment with no duplicate-dispatch protection; only then is the full unique index
replaced by a plain one. The downgrade checks that no run has more than one task
before restoring full uniqueness, and stops with a list instead of deleting anything.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4aea09600c4e'
down_revision: Union[str, Sequence[str], None] = '02b6605b5488'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTIVE = sa.text("status IN ('pending', 'claimed')")


def upgrade() -> None:
    """Upgrade schema."""
    # Expand: the narrower guarantee exists before the wider one is removed.
    op.create_index('uq_outbox_tasks_active_run', 'outbox_tasks', ['workflow_run_id'],
                    unique=True, postgresql_where=ACTIVE)
    # Contract: full uniqueness becomes a plain lookup index.
    op.drop_index(op.f('ix_outbox_tasks_workflow_run_id'), table_name='outbox_tasks')
    op.create_index(op.f('ix_outbox_tasks_workflow_run_id'), 'outbox_tasks', ['workflow_run_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    repeated = bind.execute(sa.text(
        "SELECT workflow_run_id, COUNT(*) AS n FROM outbox_tasks "
        "GROUP BY workflow_run_id HAVING COUNT(*) > 1"
    )).fetchall()
    if repeated:
        listed = ', '.join(f'{r.workflow_run_id} x{r.n}' for r in repeated[:10])
        raise RuntimeError(
            f'{len(repeated)} workflow run(s) have more than one outbox task ({listed}). '
            'Remove the extra tasks by hand before downgrading; this migration deletes nothing.'
        )
    op.drop_index(op.f('ix_outbox_tasks_workflow_run_id'), table_name='outbox_tasks')
    op.create_index(op.f('ix_outbox_tasks_workflow_run_id'), 'outbox_tasks', ['workflow_run_id'], unique=True)
    op.drop_index('uq_outbox_tasks_active_run', table_name='outbox_tasks')
