"""S3-compatible object storage adapter (C7).

Speaks the plain S3 API via boto3, so it works unmodified against real AWS S3 or any
S3-compatible endpoint (Cloudflare R2, Backblaze B2, a self-hosted MinIO/Garage) by
setting `storage_s3_endpoint_url`. Not tested against a running MinIO container in this
repo: MinIO retired its free Docker Hub/Quay distribution in September 2026 (see
docs/audit/10 DEC-034), so `tests/unit/test_s3_storage_service.py` uses `moto`'s in-process
S3 mock instead, which needs no container and no network access at all.

Streaming design mirrors `LocalFileSystemStorageService`, and deliberately does NOT hand
boto3 a live, partially-validated stream to read from directly: boto3's transfer manager
runs multipart uploads on background threads and wraps arbitrary read-time exceptions in
its own `S3UploadFailedError`, which would swallow `PayloadTooLargeError` /
`UnsupportedMediaTypeError` before `apps/api/errors.py` ever saw them. Instead, the
incoming stream is read in chunks into a `SpooledTemporaryFile` (memory-bounded; spills to
local disk past `_SPOOL_MAX_BYTES`) while this code computes the checksum and enforces the
signature/size checks itself, exactly as the local backend does for its temp file -- only
a fully-validated, already-on-disk file is ever handed to boto3, as a plain
`upload_fileobj` call with no exception-wrapping risk left to worry about.
"""

from __future__ import annotations

import hashlib
import tempfile
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from packages.domain.errors import PayloadTooLargeError
from packages.storage.magic_bytes import validate_signature
from packages.storage.service import StorageService, StoredAssetMetadata, detect_mime_type, safe_filename

_DEFAULT_CHUNK_BYTES = 1024 * 1024
_SPOOL_MAX_BYTES = 10 * 1024 * 1024  # buffer up to 10MB in memory; spill to disk past that


class S3StorageService(StorageService):
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: str = "",
        access_key_id: str = "",
        secret_access_key: str = "",
    ):
        if not bucket:
            raise ValueError("storage_s3_bucket must be set when storage_provider='s3'")
        self.bucket = bucket
        session_kwargs: dict[str, str] = {}
        if access_key_id:
            session_kwargs["aws_access_key_id"] = access_key_id
        if secret_access_key:
            session_kwargs["aws_secret_access_key"] = secret_access_key
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url or None,
            **session_kwargs,
        )

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
        filename = safe_filename(filename)
        final_mime = detect_mime_type(filename, mime_type)

        sha256 = hashlib.sha256()
        size = 0
        with tempfile.SpooledTemporaryFile(max_size=_SPOOL_MAX_BYTES) as spooled:
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
                    raise PayloadTooLargeError(f"File exceeds the {max_size_bytes} byte upload limit.")
                sha256.update(chunk)
                spooled.write(chunk)

            checksum = sha256.hexdigest()
            key = f"{safe_filename(organization_id)}/{safe_filename(project_id)}/{checksum}_{filename}"

            spooled.seek(0)
            try:
                self._client.head_object(Bucket=self.bucket, Key=key)
                # Content-addressed: an identical upload already exists under this key.
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") not in ("404", "NoSuchKey"):
                    raise
                self._client.upload_fileobj(spooled, self.bucket, key, ExtraArgs={"ContentType": final_mime})

        return StoredAssetMetadata(
            storage_path=key,
            checksum_sha256=checksum,
            size_bytes=size,
            mime_type=final_mime,
            filename=filename,
        )

    def get_stream(self, storage_path: str) -> BinaryIO:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=storage_path)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                raise FileNotFoundError(f"Stored asset not found at: {storage_path}") from exc
            raise
        return response["Body"]

    def get_bytes(self, storage_path: str) -> bytes:
        return self.get_stream(storage_path).read()

    def exists(self, storage_path: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=storage_path)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            raise
