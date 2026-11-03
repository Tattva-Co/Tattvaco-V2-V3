from packages.storage.service import (
    LocalFileSystemStorageService,
    StorageService,
    StoredAssetMetadata,
)

# Alias for convenience
LocalStorageService = LocalFileSystemStorageService

__all__ = [
    "StorageService",
    "LocalFileSystemStorageService",
    "LocalStorageService",
    "StoredAssetMetadata",
]
