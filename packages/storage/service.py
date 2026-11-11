"""Storage service interfaces and local filesystem implementation for immutable assets."""

import hashlib
import io
import mimetypes
import os
import re
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from packages.domain.errors import PayloadTooLargeError
from packages.storage.magic_bytes import FDX_MIME, validate_signature

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._ -]")
_DEFAULT_CHUNK_BYTES = 1024 * 1024

# Fountain screenplays and Final Draft XML are unknown to the stdlib mimetypes table.
mimetypes.add_type("text/plain", ".fountain")
mimetypes.add_type(FDX_MIME, ".fdx")


def detect_mime_type(filename: str, declared_mime: str | None = None) -> str:
    """Prefer a specific client-declared type; otherwise infer from the extension."""
    if declared_mime and declared_mime != "application/octet-stream":
        return declared_mime
    detected, _ = mimetypes.guess_type(filename)
    return detected or "application/octet-stream"


def safe_filename(filename: str) -> str:
    """Reduce a client-supplied filename to a single safe path/key component. Shared by
    every backend (local filesystem path segment, S3 object key segment) so "what counts
    as a safe filename" has exactly one definition."""
    name = Path(filename.replace("\\", "/")).name
    name = _UNSAFE_FILENAME_CHARS.sub("_", name).strip("._")
    return name[:200] or "upload"


@dataclass(frozen=True)
class StoredAssetMetadata:
    storage_path: str
    checksum_sha256: str
    size_bytes: int
    mime_type: str
    filename: str


class StorageService(ABC):
    """Abstract interface for object storage (local filesystem, S3, GCS, Supabase).

    `store_stream` is the one real implementation each backend provides: it must read
    `stream` in bounded chunks (never materialising the whole upload in memory at once --
    the point of this interface since C7), compute the SHA-256 checksum incrementally as
    it goes, validate the first chunk's magic-byte signature against `mime_type` when one
    is given, and raise `PayloadTooLargeError` as soon as `max_size_bytes` is exceeded
    (not after reading the rest of an oversized upload). `store_bytes` is provided for
    callers that already have the full content in memory (tests, small manual writes); it
    is never the path a real upload takes.
    """

    @abstractmethod
    def store_stream(
        self,
        stream: BinaryIO,
        filename: str,
        project_id: str,
        organization_id: str,
        mime_type: str | None = None,
        max_size_bytes: int | None = None,
        chunk_size: int = _DEFAULT_CHUNK_BYTES,
    ) -> StoredAssetMetadata:
        """Store an immutable asset stream and return its metadata."""
        pass

    def store_bytes(
        self,
        content: bytes,
        filename: str,
        project_id: str,
        organization_id: str,
        mime_type: str | None = None,
    ) -> StoredAssetMetadata:
        """Store bytes already held in memory. A thin convenience wrapper over
        `store_stream`, not a separate code path -- every backend gets this for free."""
        return self.store_stream(
            io.BytesIO(content),
            filename=filename,
            project_id=project_id,
            organization_id=organization_id,
            mime_type=mime_type,
        )

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

    _safe_filename = staticmethod(safe_filename)

    def _resolve(self, storage_path: str) -> Path:
        """Resolve a storage path, refusing anything that escapes the storage root."""
        full_path = (self.root_dir / storage_path).resolve()
        if not full_path.is_relative_to(self.root_dir):
            raise PermissionError(f"Storage path escapes storage root: {storage_path}")
        return full_path

    def store_stream(
        self,
        stream: BinaryIO,
        filename: str,
        project_id: str,
        organization_id: str,
        mime_type: str | None = None,
        max_size_bytes: int | None = None,
        chunk_size: int = _DEFAULT_CHUNK_BYTES,
    ) -> StoredAssetMetadata:
        filename = self._safe_filename(filename)
        final_mime = detect_mime_type(filename, mime_type)

        rel_dir = f"{self._safe_filename(organization_id)}/{self._safe_filename(project_id)}"
        dest_dir = self._resolve(rel_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Write to a temp file in the same directory first (so the final os.replace is an
        # atomic rename on the same filesystem, never a partial/visible-while-writing
        # file at the content-addressed path), computing the checksum as each chunk
        # arrives -- the point of streaming is that `stream` is never read in full at once.
        sha256 = hashlib.sha256()
        size = 0
        fd, tmp_path_str = tempfile.mkstemp(dir=dest_dir, prefix=".upload-")
        tmp_path = Path(tmp_path_str)
        try:
            with os.fdopen(fd, "wb") as tmp_file:
                first_chunk = True
                while True:
                    chunk = stream.read(chunk_size)
                    if not chunk:
                        break
                    if first_chunk:
                        validate_signature(final_mime, filename, chunk)
                        first_chunk = False
                    size += len(chunk)
                    if max_size_bytes is not None and size > max_size_bytes:
                        raise PayloadTooLargeError(
                            f"File exceeds the {max_size_bytes} byte upload limit."
                        )
                    sha256.update(chunk)
                    tmp_file.write(chunk)
            checksum = sha256.hexdigest()
            rel_path = f"{rel_dir}/{checksum}_{filename}"
            full_path = self._resolve(rel_path)
            if full_path.exists():
                # Content-addressed: an identical upload already exists, so the new
                # temp file is redundant -- discard it rather than rewrite the same bytes.
                tmp_path.unlink()
            else:
                os.replace(tmp_path, full_path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

        return StoredAssetMetadata(
            storage_path=rel_path,
            checksum_sha256=checksum,
            size_bytes=size,
            mime_type=final_mime,
            filename=filename,
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
