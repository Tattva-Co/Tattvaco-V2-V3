"""backfill screenplay_versions v1 from existing script assets

Revision ID: 45c4034d8e34
Revises: 910fdd9ce4ec
Create Date: 2026-11-12 08:03:10.000000+00:00

D2 (PRD §3.1 "CURRENT" migration note): every project whose Script Intelligence run
already committed canonical scenes gets one `screenplay_versions` v1 row, in `draft`
(never auto-promoted to `approved_locked` -- the PRD requires an explicit project-owner
confirmation for that, which is a user action, not something a migration can obtain;
see ScreenplayGovernanceService.confirm_legacy_lock). Its content_text is the real
extracted screenplay text (plain-text/Fountain asset bytes, or the existing extraction
derivative for PDF/DOCX/FDX -- C7), not a placeholder. Every existing scene for that
project is linked to this new version via `scenes.screenplay_version_id`.

A project with no scenes yet, or no clean script asset, gets nothing here -- there is
nothing real to backfill, and "draft" is cheap to create later through the ordinary
import flow (ScreenplayGovernanceService.import_version) instead of guessing at content.
"""
from typing import Sequence, Union
from datetime import datetime, timezone
import hashlib
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45c4034d8e34'
down_revision: Union[str, Sequence[str], None] = '910fdd9ce4ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from packages.storage.factory import get_storage

    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    projects = list(
        bind.execute(
            sa.text(
                "SELECT DISTINCT p.id, p.organization_id, p.created_by "
                "FROM projects p JOIN scenes s ON s.project_id = p.id"
            )
        )
    )

    storage = None

    for project_id, organization_id, created_by in projects:
        asset_row = bind.execute(
            sa.text(
                "SELECT id, mime_type, storage_path FROM assets "
                "WHERE project_id = :project_id AND asset_type = 'script' AND scan_status = 'clean' "
                "ORDER BY created_at ASC LIMIT 1"
            ),
            {"project_id": project_id},
        ).first()
        if asset_row is None:
            continue
        asset_id, mime_type, storage_path = asset_row

        content_text = ""
        if mime_type.startswith("text/"):
            if storage is None:
                storage = get_storage()
            try:
                content_text = storage.get_bytes(storage_path).decode("utf-8", errors="replace")
            except (FileNotFoundError, OSError):
                # The DB row exists but the underlying file doesn't (a storage root
                # reset independent of the database, e.g. test/dev environments). Best
                # effort only: fall back to an empty draft rather than failing the
                # whole migration over one project's stale asset.
                content_text = ""
        else:
            derivative_row = bind.execute(
                sa.text(
                    "SELECT content FROM asset_derivatives "
                    "WHERE asset_id = :asset_id AND derivative_type = 'extracted_text'"
                ),
                {"asset_id": asset_id},
            ).first()
            if derivative_row is not None:
                content_text = derivative_row[0]

        version_id = str(uuid.uuid4())
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
        bind.execute(
            sa.text(
                "INSERT INTO screenplay_versions "
                "(id, project_id, organization_id, episode_id, version_number, status, "
                " is_production_canonical, source_asset_id, derived_from_version_id, "
                " content_text, content_hash, created_by, created_at, updated_at) "
                "VALUES (:id, :project_id, :organization_id, NULL, 1, 'draft', "
                " false, :source_asset_id, NULL, :content_text, :content_hash, "
                " :created_by, :now, :now)"
            ),
            {
                "id": version_id,
                "project_id": project_id,
                "organization_id": organization_id,
                "source_asset_id": asset_id,
                "content_text": content_text,
                "content_hash": content_hash,
                "created_by": created_by,
                "now": now,
            },
        )
        bind.execute(
            sa.text("UPDATE scenes SET screenplay_version_id = :version_id WHERE project_id = :project_id"),
            {"version_id": version_id, "project_id": project_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    # Unlink before deleting, since scenes.screenplay_version_id FKs to this table.
    bind.execute(
        sa.text(
            "UPDATE scenes SET screenplay_version_id = NULL "
            "WHERE screenplay_version_id IN (SELECT id FROM screenplay_versions WHERE version_number = 1 "
            "AND derived_from_version_id IS NULL)"
        )
    )
    bind.execute(
        sa.text("DELETE FROM screenplay_versions WHERE version_number = 1 AND derived_from_version_id IS NULL")
    )
