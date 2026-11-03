"""Alembic autogenerate filters.

The LangGraph PostgresSaver creates and migrates its own tables (``checkpoints``,
``checkpoint_blobs``, ``checkpoint_writes``, ``checkpoint_migrations``) in the same
database. They are not part of our ORM metadata, so without this filter
``alembic revision --autogenerate`` would emit DROP TABLE statements for them and
destroy in-flight workflow state.
"""

LANGGRAPH_TABLE_PREFIX = "checkpoint"


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name and name.startswith(LANGGRAPH_TABLE_PREFIX):
        return False
    table = getattr(obj, "table", None)
    if type_ in ("index", "column", "unique_constraint", "foreign_key_constraint") and table is not None:
        if table.name.startswith(LANGGRAPH_TABLE_PREFIX):
            return False
    return True
