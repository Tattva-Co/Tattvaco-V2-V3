"""Construct the configured storage provider."""

from functools import lru_cache

from packages.core.config import get_settings
from packages.storage.service import LocalFileSystemStorageService, StorageService


@lru_cache
def get_storage() -> StorageService:
    settings = get_settings()
    if settings.storage_provider == "local":
        return LocalFileSystemStorageService(root_dir=settings.storage_local_root)
    if settings.storage_provider == "s3":
        # Imported lazily: boto3 is a real dependency only once S3 is actually selected,
        # so "local" (the dev/test default) never pays for importing it.
        from packages.storage.s3_service import S3StorageService

        return S3StorageService(
            bucket=settings.storage_s3_bucket,
            region=settings.storage_s3_region,
            endpoint_url=settings.storage_s3_endpoint_url,
            access_key_id=settings.storage_s3_access_key_id,
            secret_access_key=settings.storage_s3_secret_access_key,
        )
    raise ValueError(f"Unsupported storage provider: {settings.storage_provider}")
