"""Immutable asset upload and listing."""

from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from apps.api.dependencies import Settings, StorageService, get_actor, get_db, get_settings, get_storage
from apps.api.schemas import AssetResponse, AssetUploadResponse
from packages.domain.errors import PayloadTooLargeError
from packages.services.assets import AssetService
from packages.services.identity import ActorContext

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    settings: Settings = Depends(get_settings),
):
    # Read at most limit+1 bytes so an oversized upload is rejected without buffering it all.
    content = await file.read(settings.storage_max_upload_bytes + 1)
    if len(content) > settings.storage_max_upload_bytes:
        raise PayloadTooLargeError(
            f"File exceeds the {settings.storage_max_upload_bytes} byte upload limit."
        )
    asset = AssetService(db, storage, settings).upload(
        actor,
        project_id,
        filename=file.filename or "script.fountain",
        content=content,
        declared_mime=file.content_type,
    )
    return AssetUploadResponse(
        asset_id=asset.id,
        filename=asset.filename,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        checksum_sha256=asset.checksum_sha256,
        storage_path=asset.storage_path,
    )


@router.get("", response_model=List[AssetResponse])
def list_assets(
    project_id: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    settings: Settings = Depends(get_settings),
):
    return AssetService(db, storage, settings).list(actor, project_id)
