"""Malware scanning seam (C7).

An uploaded asset is QUARANTINED until scanned CLEAN (packages.domain.enums
AssetScanStatus) -- no workflow may read its content before that
(packages.services.script_review.ScriptReviewService.load_script_text enforces this).
Today the only implementation is a no-op stub that always reports clean, synchronously, at
upload time. This file exists so swapping in a real scanner (ClamAV via clamd, a cloud
scanning API) later is a one-class change behind `get_scanner`, not a refactor: a real
scanner would likely run asynchronously (its own outbox task), leaving an asset visibly
QUARANTINED for a real interval -- the state model already supports that, nothing else
needs to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from packages.core.config import Settings
from packages.domain.enums import AssetScanStatus
from packages.storage.service import StorageService


@dataclass(frozen=True)
class ScanResult:
    status: AssetScanStatus
    details: str | None = None


class ScannerService(ABC):
    @abstractmethod
    def scan(self, storage: StorageService, storage_path: str, filename: str, mime_type: str) -> ScanResult:
        """Scan an already-validated (signature-checked, size-checked) stored asset.

        Takes the storage backend and path rather than content bytes: a real scanner
        (e.g. ClamAV's clamd, over its INSTREAM protocol) reads the asset back as a
        stream and scans it in chunks, the same way AssetService.upload_stream wrote it
        -- keeping the "never materialise a whole large upload in memory" property intact
        end to end, not just at the storage layer.
        """


class NoOpScanner(ScannerService):
    """Dev/test default: reports every asset clean without inspecting it (never even
    opens the stream). Labelled explicitly (not silently) wherever it is used, so it's
    never mistaken for a real scan having happened -- see AssetService.upload_stream's
    audit log entry."""

    def scan(self, storage: StorageService, storage_path: str, filename: str, mime_type: str) -> ScanResult:
        return ScanResult(status=AssetScanStatus.CLEAN, details="noop scanner: not actually inspected")


def get_scanner(settings: Settings) -> ScannerService:
    if settings.malware_scanner_provider == "noop":
        return NoOpScanner()
    raise ValueError(f"Unsupported malware scanner provider: {settings.malware_scanner_provider}")
