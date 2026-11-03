"""Construct the configured storage provider."""

from functools import lru_cache

from packages.core.config import get_settings
from packages.storage.service import LocalFileSystemStorageService, StorageService


@lru_cache
def get_storage() -> StorageService:
    settings = get_settings()
    if settings.storage_provider == "local":
        return LocalFileSystemStorageService(root_dir=settings.storage_local_root)
    raise ValueError(f"Unsupported storage provider: {settings.storage_provider}")
