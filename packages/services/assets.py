"""Immutable asset ingestion with upload policy enforcement (C7: streaming, scanning,
magic-byte validation, and real text extraction for non-plain-text screenplay formats)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import BinaryIO, List

from sqlalchemy.orm import Session

from packages.core.config import Settings
from packages.domain.enums import AssetScanStatus, AssetType, AuditAction
from packages.domain.errors import AssetNotReadyError, UnsupportedMediaTypeError, ValidationFailure
from packages.persistence.models import AssetDerivativeModel, AssetModel
from packages.persistence.repositories import (
    AssetDerivativeRepository,
    AssetRepository,
    AuditRepository,
    ProjectRepository,
)
from packages.services.authz import AuthzService
from packages.services.extraction import EXTRACTABLE_MIME_TYPES, extract_text
from packages.services.identity import ActorContext
from packages.services.scanning import ScannerService, get_scanner
from packages.storage.service import StorageService, detect_mime_type

DERIVATIVE_TYPE_EXTRACTED_TEXT = "extracted_text"


class AssetService:
    def __init__(self, db: Session, storage: StorageService, settings: Settings, scanner: ScannerService | None = None):
        self.db = db
        self.storage = storage
        self.settings = settings
        self.scanner = scanner or get_scanner(settings)
        self.assets = AssetRepository(db)
        self.derivatives = AssetDerivativeRepository(db)
        self.projects = ProjectRepository(db)
        self.audit = AuditRepository(db)
        self.authz = AuthzService(db)

    def upload_stream(
        self,
        actor: ActorContext,
        project_id: str,
        *,
        filename: str,
        stream: BinaryIO,
        declared_mime: str | None = None,
        asset_type: AssetType = AssetType.SCRIPT,
    ) -> AssetModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "asset.upload", project)

        mime = detect_mime_type(filename, declared_mime)
        if mime not in self.settings.storage_allowed_mime_types:
            raise UnsupportedMediaTypeError(f"File type '{mime}' is not allowed.")

        # The whole point of streaming: `stream` is read here in bounded chunks (the
        # magic-byte signature check and size-limit enforcement happen inline, inside
        # store_stream, as each chunk arrives), never as one in-memory blob -- this is
        # what keeps a multi-gigabyte upload from spiking API process memory.
        stored = self.storage.store_stream(
            stream,
            filename=filename,
            project_id=project.id,
            organization_id=project.organization_id,
            mime_type=mime,
            max_size_bytes=self.settings.storage_max_upload_bytes,
            chunk_size=self.settings.storage_stream_chunk_bytes,
        )
        if stored.size_bytes == 0:
            raise ValidationFailure("Uploaded file is empty.")

        asset = self.assets.add(
            AssetModel(
                project_id=project.id,
                organization_id=project.organization_id,
                filename=stored.filename,
                mime_type=stored.mime_type,
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                storage_path=stored.storage_path,
                asset_type=asset_type.value,
                is_original=True,
                uploaded_by=actor.user_id,
                asset_metadata={"uploaded_filename": filename},
                scan_status=AssetScanStatus.QUARANTINED.value,
            )
        )
        self.db.flush()  # assigns asset.id, needed below and for the audit target

        scan = self.scanner.scan(self.storage, stored.storage_path, stored.filename, stored.mime_type)
        asset.scan_status = scan.status.value
        asset.scanned_at = datetime.now(UTC)

        if scan.status == AssetScanStatus.CLEAN and stored.mime_type in EXTRACTABLE_MIME_TYPES:
            # Extraction needs the full document in memory to parse its structure (PDF/
            # DOCX/XML libraries have no streaming-parse API) -- unlike the store path
            # above, this is a deliberate, bounded exception: it only runs for screenplay
            # DOCUMENT formats, which in practice are at most a few tens of MB, never for
            # the large media uploads the streaming store path exists to protect against.
            content = self.storage.get_bytes(stored.storage_path)
            result = extract_text(content, stored.mime_type, stored.filename)
            self.derivatives.upsert(
                AssetDerivativeModel(
                    asset_id=asset.id,
                    project_id=project.id,
                    organization_id=project.organization_id,
                    derivative_type=DERIVATIVE_TYPE_EXTRACTED_TEXT,
                    extractor=result.extractor,
                    content=result.text,
                    extraction_error=result.error,
                )
            )

        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.ASSET_UPLOADED,
            target_type="asset",
            target_id=asset.id,
            details={
                "filename": asset.filename,
                "checksum_sha256": asset.checksum_sha256,
                "scan_status": asset.scan_status,
            },
        )
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def require_clean(self, asset: AssetModel) -> None:
        if asset.scan_status != AssetScanStatus.CLEAN.value:
            raise AssetNotReadyError(
                f"Asset '{asset.id}' is not usable yet (scan_status={asset.scan_status!r})."
            )

    def list(self, actor: ActorContext, project_id: str) -> List[AssetModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.assets.list_for_project(project_id)
