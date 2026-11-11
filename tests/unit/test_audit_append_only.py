"""audit_events is append-only (C8): a BEFORE UPDATE OR DELETE trigger
(prevent_audit_event_mutation, migration 509b44e10054) raises unless the session has
explicitly set `tattva.allow_audit_mutation = 'true'` first -- the one legitimate use of
which in this codebase is tests/support.py::purge_organization's own teardown.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from packages.persistence.database import SessionLocal
from packages.persistence.models import AuditEventModel
from tests.support import create_project


def _insert_audit_row(db, *, project_id: str, organization_id: str, actor_id: str) -> str:
    row = AuditEventModel(
        project_id=project_id,
        organization_id=organization_id,
        actor_id=actor_id,
        action="test_event",
        target_type="test",
        target_id="target-1",
        details={},
    )
    db.add(row)
    db.flush()
    return row.id


def test_update_without_the_override_is_rejected(client, tenant):
    project = create_project(client, tenant)
    db = SessionLocal()
    try:
        row_id = _insert_audit_row(
            db, project_id=project["id"], organization_id=tenant.org_id, actor_id=tenant.user_id
        )
        db.commit()

        with pytest.raises(ProgrammingError, match="append-only"):
            db.execute(text("UPDATE audit_events SET action = 'tampered' WHERE id = :id"), {"id": row_id})
        db.rollback()
    finally:
        db.close()


def test_delete_without_the_override_is_rejected(client, tenant):
    project = create_project(client, tenant)
    db = SessionLocal()
    try:
        row_id = _insert_audit_row(
            db, project_id=project["id"], organization_id=tenant.org_id, actor_id=tenant.user_id
        )
        db.commit()

        with pytest.raises(ProgrammingError, match="append-only"):
            db.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": row_id})
        db.rollback()
    finally:
        db.close()


def test_insert_is_always_allowed(client, tenant):
    """The trigger only guards UPDATE/DELETE -- ordinary audit logging (every
    AuditRepository.record call across the app) is completely unaffected."""
    project = create_project(client, tenant)
    db = SessionLocal()
    try:
        _insert_audit_row(db, project_id=project["id"], organization_id=tenant.org_id, actor_id=tenant.user_id)
        db.commit()
    finally:
        db.close()


def test_the_scoped_override_permits_mutation_for_the_duration_of_one_transaction(client, tenant):
    project = create_project(client, tenant)
    db = SessionLocal()
    try:
        row_id = _insert_audit_row(
            db, project_id=project["id"], organization_id=tenant.org_id, actor_id=tenant.user_id
        )
        db.commit()

        db2 = SessionLocal()
        try:
            db2.execute(text("SET LOCAL tattva.allow_audit_mutation = 'true'"))
            db2.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": row_id})
            db2.commit()
        finally:
            db2.close()

        # The row really is gone (the override worked, not a silent no-op)...
        db3 = SessionLocal()
        try:
            remaining = db3.execute(
                text("SELECT 1 FROM audit_events WHERE id = :id"), {"id": row_id}
            ).first()
            assert remaining is None

            # ...and the override does not leak into a new session/transaction: mutating
            # a *different* row here, with no SET LOCAL, is rejected exactly as before.
            other_row_id = _insert_audit_row(
                db3, project_id=project["id"], organization_id=tenant.org_id, actor_id=tenant.user_id
            )
            db3.commit()
            with pytest.raises(ProgrammingError, match="append-only"):
                db3.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": other_row_id})
            db3.rollback()
        finally:
            db3.close()
    finally:
        db.close()


# tests/conftest.py's `tenant` fixture calls purge_organization(org_id) in its own
# teardown for every single test in the suite, and every test that uploads a script
# (upload_script -> AuditAction.ASSET_UPLOADED) leaves real audit_events rows for it to
# delete -- the full suite passing at all is already the end-to-end proof that
# purge_organization's SET LOCAL override keeps working through this trigger, so no
# separate test duplicates that here.
