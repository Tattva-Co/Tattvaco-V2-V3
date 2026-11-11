"""add generator_mode to workflow_runs and candidate tables

Revision ID: b8a9dc799b50
Revises: 509b44e10054
Create Date: 2026-11-11 13:35:23.740023+00:00

C10 (packages/ai/gateway.py): expand -> backfill -> contract, same pattern as every
prior migration adding a required column to a non-empty table. Every run and candidate
that exists before this migration was produced by one of the 4 pre-existing rule-based
generators, which is exactly what GENERATOR_MODE_DETERMINISTIC ("deterministic") now
names -- backfilling to it is not a guess, it is what actually happened.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8a9dc799b50'
down_revision: Union[str, Sequence[str], None] = '509b44e10054'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = (
    "entity_candidates",
    "film_bible_rule_candidates",
    "research_claim_candidates",
    "research_question_candidates",
    "scene_candidates",
    "storyboard_panel_candidates",
    "workflow_runs",
)


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("generator_mode", sa.String(length=20), nullable=False, server_default="deterministic"),
        )
    for table in _TABLES:
        op.alter_column(table, "generator_mode", server_default=None)


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "generator_mode")
