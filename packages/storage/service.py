"""Storage service interfaces and local filesystem implementation for immutable assets."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import mimetypes
import re
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._ -]")


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

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Reduce a client-supplied filename to a single safe path component."""
        name = Path(filename.replace("\\", "/")).name
        name = _UNSAFE_FILENAME_CHARS.sub("_", name).strip("._")
        return name[:200] or "upload"

    def _resolve(self, storage_path: str) -> Path:
        """Resolve a storage path, refusing anything that escapes the storage root."""
        full_path = (self.root_dir / storage_path).resolve()
        if not full_path.is_relative_to(self.root_dir):
            raise PermissionError(f"Storage path escapes storage root: {storage_path}")
        return full_path

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
        filename = self._safe_filename(filename)
        checksum, size = self._compute_checksum_and_size(content)
        final_mime = self._detect_mime_type(filename, mime_type)

        # Content-addressed deterministic immutable path scoped by tenant and project
        rel_path = (
            f"{self._safe_filename(organization_id)}/{self._safe_filename(project_id)}/"
            f"{checksum}_{filename}"
        )
        full_path = self._resolve(rel_path)
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
        full_path = self._resolve(storage_path)
        if not full_path.exists():
            raise FileNotFoundError(f"Stored asset not found at: {storage_path}")
        return open(full_path, "rb")

    def get_bytes(self, storage_path: str) -> bytes:
        full_path = self._resolve(storage_path)
        if not full_path.exists():
            raise FileNotFoundError(f"Stored asset not found at: {storage_path}")
        with open(full_path, "rb") as f:
            return f.read()

    def exists(self, storage_path: str) -> bool:
        try:
            return self._resolve(storage_path).exists()
        except PermissionError:
            return False
