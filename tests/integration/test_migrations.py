"""Guards that Alembic migrations and ORM models stay in sync.

Also guards against autogenerate proposing to drop the LangGraph checkpointer tables,
which share the database but are owned by LangGraph, not by our migrations.
"""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from packages.persistence.database import Base, engine
from packages.persistence.migration_filters import include_object


def test_models_match_migrated_schema():
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"include_object": include_object})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"Schema drift between models and migrations: {diff}"
