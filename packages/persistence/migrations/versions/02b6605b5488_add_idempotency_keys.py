"""add_idempotency_keys

Revision ID: 02b6605b5488
Revises: ab1dac6edef2
Create Date: 2026-11-06 09:30:00+00:00

Stores client Idempotency-Keys and the response each produced, so a retried POST
replays its first result instead of running twice (TFD-OPS-004; plan C6). New table
only; no existing data is touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02b6605b5488'
down_revision: Union[str, Sequence[str], None] = 'ab1dac6edef2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'idempotency_keys',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('path', sa.String(length=500), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.LargeBinary(), nullable=True),
        sa.Column('response_content_type', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_idempotency_keys_organization_id'), 'idempotency_keys', ['organization_id'], unique=False)
    op.create_index('uq_idempotency_keys_org_user_key', 'idempotency_keys',
                    ['organization_id', 'user_id', 'key'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_idempotency_keys_org_user_key', table_name='idempotency_keys')
    op.drop_index(op.f('ix_idempotency_keys_organization_id'), table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
