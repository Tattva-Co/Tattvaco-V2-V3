"""S3StorageService against an in-process mock (moto), not a real/MinIO container --
MinIO's free Docker distribution was retired in Sept 2026 (docs/audit/10 DEC-034). `moto`
needs no network access and no Docker, so these tests actually run anywhere pytest does.

Mirrors tests/integration/test_storage_service.py's local-filesystem coverage, proving the
two backends behave the same way behind the shared `StorageService` interface.
"""

from __future__ import annotations

import hashlib
import io

import boto3
import pytest
from moto import mock_aws

from packages.domain.errors import PayloadTooLargeError, UnsupportedMediaTypeError
from packages.storage.s3_service import S3StorageService

BUCKET = "tattva-test-assets"


@pytest.fixture
def s3_storage():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield S3StorageService(bucket=BUCKET, region="us-east-1")


def test_stores_and_retrieves_asset(s3_storage):
    content = b"%PDF-1.4\n%fake pdf content for signature matching\n"
    expected_sha = hashlib.sha256(content).hexdigest()

    stored = s3_storage.store_stream(
        io.BytesIO(content),
        filename="script.pdf",
        project_id="proj-123",
        organization_id="org-abc",
        mime_type="application/pdf",
    )

    assert stored.checksum_sha256 == expected_sha
    assert stored.size_bytes == len(content)
    assert s3_storage.exists(stored.storage_path)
    assert s3_storage.get_bytes(stored.storage_path) == content


def test_content_addressed_dedup_skips_a_redundant_upload(s3_storage):
    content = b"INT. THRONE ROOM - NIGHT\n"

    stored1 = s3_storage.store_bytes(content, "scene.fountain", "proj-1", "org-1", mime_type="text/plain")
    stored2 = s3_storage.store_bytes(content, "scene.fountain", "proj-1", "org-1", mime_type="text/plain")

    assert stored1.checksum_sha256 == stored2.checksum_sha256
    assert stored1.storage_path == stored2.storage_path


def test_rejects_a_stream_over_the_max_size(s3_storage):
    content = b"x" * 1000
    with pytest.raises(PayloadTooLargeError):
        s3_storage.store_stream(
            io.BytesIO(content),
            filename="big.txt",
            project_id="proj-1",
            organization_id="org-1",
            mime_type="text/plain",
            max_size_bytes=500,
            chunk_size=100,
        )


def test_rejects_content_whose_signature_does_not_match_its_declared_type(s3_storage):
    # Plain text content uploaded as if it were a PDF: no %PDF- signature.
    content = b"This is not actually a PDF file at all."
    with pytest.raises(UnsupportedMediaTypeError):
        s3_storage.store_stream(
            io.BytesIO(content),
            filename="fake.pdf",
            project_id="proj-1",
            organization_id="org-1",
            mime_type="application/pdf",
        )


def test_get_bytes_raises_file_not_found_for_a_missing_key(s3_storage):
    with pytest.raises(FileNotFoundError):
        s3_storage.get_bytes("org-1/proj-1/does-not-exist.txt")


def test_exists_is_false_for_a_missing_key(s3_storage):
    assert s3_storage.exists("org-1/proj-1/does-not-exist.txt") is False
