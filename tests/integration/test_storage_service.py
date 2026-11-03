"""Integration tests for the immutable storage service."""

import hashlib
import tempfile
from pathlib import Path

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
