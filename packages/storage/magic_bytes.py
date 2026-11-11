"""Magic-byte (file signature) validation.

A client-declared Content-Type or a filename extension can both be spoofed trivially
(rename a renamed file). This checks the first chunk of actual bytes against the known
binary signature for the type the upload claims to be, and raises if they disagree --
catching, for example, an arbitrary file renamed to `.pdf` to slip past the MIME
allowlist.

Deliberately dependency-free (no `python-magic`/libmagic): the allowlist
(packages.core.config.Settings.storage_allowed_mime_types) only ever contains a handful of
formats, and each has either a well-known fixed signature or no binary signature at all (in
which case the check is "does this look like text, not binary").
"""

from __future__ import annotations

from packages.domain.errors import UnsupportedMediaTypeError

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
FDX_MIME = "application/x-final-draft"

_PDF_SIGNATURE = b"%PDF-"
# DOCX (and every other OOXML/zip-based office format) is a zip archive; these are the
# three signatures a zip file can legally start with (the third is an empty archive).
_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_TEXT_LIKE_MIME_TYPES = frozenset({"text/plain", "application/json", FDX_MIME})


def signature_matches(mime_type: str, first_chunk: bytes) -> bool:
    """True if `first_chunk` (the start of the file, at least a few hundred bytes when
    available) looks consistent with `mime_type`. An empty file is handled separately by
    the caller (AssetService.validate_upload rejects empty uploads outright), so an empty
    `first_chunk` here is treated as matching -- there's nothing to contradict yet.
    """
    if not first_chunk:
        return True
    if mime_type == "application/pdf":
        return first_chunk.startswith(_PDF_SIGNATURE)
    if mime_type == DOCX_MIME:
        return first_chunk.startswith(_ZIP_SIGNATURES)
    if mime_type in _TEXT_LIKE_MIME_TYPES:
        # No binary signature exists for plain text; a NUL byte is the one thing that
        # never legitimately appears in real text content, so its presence means the
        # content is binary data wearing a text extension.
        return b"\x00" not in first_chunk
    # An allowlisted type this module has no signature for (should not happen with the
    # current allowlist, but a future addition shouldn't be silently blocked): don't
    # enforce a check we don't actually have.
    return True


def validate_signature(mime_type: str, filename: str, first_chunk: bytes) -> None:
    if not signature_matches(mime_type, first_chunk):
        raise UnsupportedMediaTypeError(
            f"'{filename}' does not look like a valid {mime_type} file "
            "(its content does not match its declared type)."
        )
