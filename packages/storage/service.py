"""Storage service interfaces and local filesystem implementation for immutable assets."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import mimetypes
import os
from pathlib import Path
from typing import BinaryIO, Optional, Tuple


@dataclass(frozen=True)
class StoredAssetMetadata:
    storage_path: str
    checksum_sha256: str
    size_bytes: int
    mime_type: str
    filename: str


class StorageService(ABC):
    """Abstract interface for object storage (local filesystem, S3, GCS, Supabase)."""

    @abstractmethod
    def store_stream(
        self,
        stream: BinaryIO,
        filename: str,
        project_id: str,
        organization_id: str,
        mime_type: Optional[str] = None,
    ) -> StoredAssetMetadata:
        """Store an immutable asset stream and return its metadata."""
        pass

    @abstractmethod
    def store_bytes(
        self,
        content: bytes,
        filename: str,
        project_id: str,
        organization_id: str,
        mime_type: Optional[str] = None,
    ) -> StoredAssetMetadata:
        """Store bytes and return asset metadata."""
        pass

    @abstractmethod
    def get_stream(self, storage_path: str) -> BinaryIO:
        """Retrieve stored asset as a readable binary stream."""
        pass

    @abstractmethod
    def get_bytes(self, storage_path: str) -> bytes:
        """Retrieve stored asset content as bytes."""
        pass

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """Check if an asset exists at the specified path."""
        pass


class LocalFileSystemStorageService(StorageService):
    """Local filesystem storage provider for offline development and deterministic testing."""

    def __init__(self, root_dir: str = "./data/storage"):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _compute_checksum_and_size(self, content: bytes) -> Tuple[str, int]:
        sha256 = hashlib.sha256(content).hexdigest()
        return sha256, len(content)

    def _detect_mime_type(self, filename: str, explicit_mime: Optional[str] = None) -> str:
        if explicit_mime and explicit_mime != "application/octet-stream":
            return explicit_mime
        detected, _ = mimetypes.guess_type(filename)
        return detected or "application/octet-stream"

    def store_bytes(
        self,
        content: bytes,
        filename: str,
        project_id: str,
        organization_id: str,
        mime_type: Optional[str] = None,
    ) -> StoredAssetMetadata:
        checksum, size = self._compute_checksum_and_size(content)
        final_mime = self._detect_mime_type(filename, mime_type)

        # Content-addressed deterministic immutable path scoped by tenant and project
        rel_path = f"{organization_id}/{project_id}/{checksum}_{filename}"
        full_path = self.root_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if not full_path.exists():
            with open(full_path, "wb") as f:
                f.write(content)

        return StoredAssetMetadata(
            storage_path=str(rel_path),
            checksum_sha256=checksum,
            size_bytes=size,
            mime_type=final_mime,
            filename=filename,
        )

    def store_stream(
        self,
        stream: BinaryIO,
        filename: str,
        project_id: str,
        organization_id: str,
        mime_type: Optional[str] = None,
    ) -> StoredAssetMetadata:
        content = stream.read()
        return self.store_bytes(
            content=content,
            filename=filename,
            project_id=project_id,
            organization_id=organization_id,
            mime_type=mime_type,
        )

    def get_stream(self, storage_path: str) -> BinaryIO:
        full_path = self.root_dir / storage_path
        if not full_path.exists():
            raise FileNotFoundError(f"Stored asset not found at: {storage_path}")
        return open(full_path, "rb")

    def get_bytes(self, storage_path: str) -> bytes:
        full_path = self.root_dir / storage_path
        if not full_path.exists():
            raise FileNotFoundError(f"Stored asset not found at: {storage_path}")
        with open(full_path, "rb") as f:
            return f.read()

    def exists(self, storage_path: str) -> bool:
        full_path = self.root_dir / storage_path
        return full_path.exists()
