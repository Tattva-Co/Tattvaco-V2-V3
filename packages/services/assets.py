"""Immutable asset ingestion with upload policy enforcement."""

from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from packages.core.config import Settings
from packages.domain.enums import AssetType, AuditAction
from packages.domain.errors import PayloadTooLargeError, UnsupportedMediaTypeError, ValidationFailure
from packages.persistence.models import AssetModel
from packages.persistence.repositories import AssetRepository, AuditRepository, ProjectRepository
from packages.services.identity import ActorContext
from packages.storage.service import StorageService, detect_mime_type


class AssetService:
    def __init__(self, db: Session, storage: StorageService, settings: Settings):
        self.db = db
        self.storage = storage
        self.settings = settings
        self.assets = AssetRepository(db)
        self.projects = ProjectRepository(db)
        self.audit = AuditRepository(db)

    def validate_upload(self, filename: str, size_bytes: int, declared_mime: str | None) -> str:
        """Apply upload policy; returns the effective MIME type."""
        if size_bytes == 0:
            raise ValidationFailure("Uploaded file is empty.")
        if size_bytes > self.settings.storage_max_upload_bytes:
            raise PayloadTooLargeError(
                f"File exceeds the {self.settings.storage_max_upload_bytes} byte upload limit."
            )
        mime = detect_mime_type(filename, declared_mime)
        if mime not in self.settings.storage_allowed_mime_types:
            raise UnsupportedMediaTypeError(f"File type '{mime}' is not allowed.")
        return mime

    def upload(
        self,
        actor: ActorContext,
        project_id: str,
        *,
        filename: str,
        content: bytes,
        declared_mime: str | None = None,
        asset_type: AssetType = AssetType.SCRIPT,
    ) -> AssetModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        mime = self.validate_upload(filename, len(content), declared_mime)

        stored = self.storage.store_bytes(
            content=content,
            filename=filename,
            project_id=project.id,
            organization_id=project.organization_id,
            mime_type=mime,
        )
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
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.ASSET_UPLOADED,
            target_type="asset",
            target_id=asset.id,
            details={"filename": asset.filename, "checksum_sha256": asset.checksum_sha256},
        )
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def list(self, actor: ActorContext, project_id: str) -> List[AssetModel]:
        self.projects.get_scoped(project_id, actor.org_id)
        return self.assets.list_for_project(project_id)
