"""Immutable asset upload and listing."""

from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from apps.api.dependencies import Settings, StorageService, get_actor, get_db, get_settings, get_storage
from apps.api.schemas import AssetResponse, AssetUploadResponse
from packages.services.assets import AssetService
from packages.services.identity import ActorContext

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])


@router.post("/upload", response_model=AssetUploadResponse)
def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    settings: Settings = Depends(get_settings),
):
    # `file.file` is Starlette's underlying spooled file (in memory up to its own small
    # threshold, then disk-backed) -- AssetService.upload_stream reads it in bounded
    # chunks from here on, so the request body is never materialised as one giant `bytes`
    # object (C7: a 2GB upload must not spike API process memory). Not `async def`: every
    # layer below (the SQLAlchemy session, the storage/scan/extraction calls) is already
    # synchronous, same as every other route in this file -- making only this one `async`
    # bought nothing but a confusing read-vs-everything-else split.
    asset = AssetService(db, storage, settings).upload_stream(
        actor,
        project_id,
        filename=file.filename or "script.fountain",
        stream=file.file,
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
