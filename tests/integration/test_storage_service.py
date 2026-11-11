"""Integration tests for the immutable storage service."""

import hashlib
import io
import tempfile
from pathlib import Path

import pytest

from packages.domain.errors import PayloadTooLargeError, UnsupportedMediaTypeError
from packages.storage.service import LocalFileSystemStorageService


def test_storage_service_stores_and_retrieves_asset():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalFileSystemStorageService(root_dir=tmpdir)
        content = b"EXT. FORT COURTYARD - DAY\nWarrior stands tall.\n"
        expected_sha = hashlib.sha256(content).hexdigest()

        stored = storage.store_bytes(
            content=content,
            filename="test_script.fountain",
            project_id="proj-123",
            organization_id="org-abc",
            mime_type="text/plain",
        )

        assert stored.checksum_sha256 == expected_sha
        assert stored.size_bytes == len(content)
        assert storage.exists(stored.storage_path)

        retrieved = storage.get_bytes(stored.storage_path)
        assert retrieved == content


def test_storage_service_immutability():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalFileSystemStorageService(root_dir=tmpdir)
        content = b"INT. THRONE ROOM - NIGHT\n"

        stored1 = storage.store_bytes(
            content=content,
            filename="scene.fountain",
            project_id="proj-1",
            organization_id="org-1",
        )

        # Storing identical content yields identical checksum and path
        stored2 = storage.store_bytes(
            content=content,
            filename="scene.fountain",
            project_id="proj-1",
            organization_id="org-1",
        )

        assert stored1.checksum_sha256 == stored2.checksum_sha256
        assert stored1.storage_path == stored2.storage_path


def test_storage_service_neutralises_path_traversal_in_filename():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "storage"
        storage = LocalFileSystemStorageService(root_dir=str(root))

        stored = storage.store_bytes(
            content=b"payload",
            filename="../../../escaped.txt",
            project_id="proj-1",
            organization_id="org-1",
        )

        written = (root / stored.storage_path).resolve()
        assert written.is_relative_to(root.resolve())
        assert not (Path(tmpdir) / "escaped.txt").exists()
        assert stored.filename == "escaped.txt"


def test_storage_service_rejects_read_outside_root():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalFileSystemStorageService(root_dir=str(Path(tmpdir) / "storage"))
        (Path(tmpdir) / "secret.txt").write_text("nope")

        try:
            storage.get_bytes("../secret.txt")
        except (PermissionError, FileNotFoundError):
            pass
        else:
            raise AssertionError("Reading outside the storage root must be refused")


def test_store_stream_reads_in_bounded_chunks_and_produces_the_same_checksum(tmp_path):
    """The point of C7's streaming rewrite: a small chunk_size still reconstructs exactly
    the original bytes and checksum, proving the multi-chunk read/write loop is correct
    (not just the historical single `.read()` path)."""
    storage = LocalFileSystemStorageService(root_dir=str(tmp_path))
    content = b"INT. FORT COURTYARD - DAY\n" + b"A line of dialogue.\n" * 500
    expected_sha = hashlib.sha256(content).hexdigest()

    stored = storage.store_stream(
        io.BytesIO(content),
        filename="big_scene.fountain",
        project_id="proj-1",
        organization_id="org-1",
        mime_type="text/plain",
        chunk_size=64,  # deliberately tiny, forcing many read iterations
    )

    assert stored.checksum_sha256 == expected_sha
    assert stored.size_bytes == len(content)
    assert storage.get_bytes(stored.storage_path) == content


def test_store_stream_rejects_a_stream_over_the_max_size_and_cleans_up(tmp_path):
    storage = LocalFileSystemStorageService(root_dir=str(tmp_path))
    content = b"x" * 1000

    with pytest.raises(PayloadTooLargeError):
        storage.store_stream(
            io.BytesIO(content),
            filename="too_big.txt",
            project_id="proj-1",
            organization_id="org-1",
            mime_type="text/plain",
            max_size_bytes=500,
            chunk_size=100,
        )

    # No stray temp file (or anything else) left behind under the org/project directory.
    leftover = list((tmp_path / "org-1" / "proj-1").iterdir()) if (tmp_path / "org-1" / "proj-1").exists() else []
    assert leftover == []


def test_store_stream_rejects_content_whose_signature_does_not_match_its_declared_type(tmp_path):
    storage = LocalFileSystemStorageService(root_dir=str(tmp_path))
    content = b"This is not actually a PDF file at all."

    with pytest.raises(UnsupportedMediaTypeError):
        storage.store_stream(
            io.BytesIO(content),
            filename="fake.pdf",
            project_id="proj-1",
            organization_id="org-1",
            mime_type="application/pdf",
        )


def test_store_bytes_is_a_thin_wrapper_over_store_stream(tmp_path):
    """store_bytes (used by tests and any small in-memory write) must behave identically
    to store_stream, since it is now implemented purely in terms of it."""
    storage = LocalFileSystemStorageService(root_dir=str(tmp_path))
    content = b"%PDF-1.4\nfake but signature-valid pdf bytes\n"

    stored = storage.store_bytes(content, "doc.pdf", "proj-1", "org-1", mime_type="application/pdf")

    assert stored.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert storage.get_bytes(stored.storage_path) == content
