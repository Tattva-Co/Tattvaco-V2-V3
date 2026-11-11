"""Real text extraction for non-plain-text screenplay formats (C7).

Before this, only `text/*` assets (Fountain, .txt) were usable at all --
ScriptReviewService.load_script_text rejected anything else outright. A PDF or Word
screenplay could be uploaded (both are in the upload allowlist for other purposes, e.g.
research sources) but never actually fed to Script Intelligence. This extracts real,
structured plain text from PDF, DOCX and Final Draft (.fdx) so they can be, producing text
shaped the way packages/workflows/script_intelligence/parser.py already expects: one
slugline per line ("INT. LOCATION - DAY"), one character cue per line (an uppercase line
on its own), everything else as action/dialogue prose.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from defusedxml.ElementTree import fromstring as safe_xml_fromstring
from docx import Document
from pypdf import PdfReader

from packages.storage.magic_bytes import DOCX_MIME, FDX_MIME

EXTRACTABLE_MIME_TYPES = frozenset({"application/pdf", DOCX_MIME, FDX_MIME})


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    extractor: str
    error: str | None = None


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _extract_docx(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_fdx(content: bytes) -> str:
    """Final Draft XML: <FinalDraft><Content><Paragraph Type="..."><Text>...</Text>...
    One output line per Paragraph (its Text children's content concatenated), which
    reproduces the plain-text shape a Fountain-style script would have -- a scene heading
    or character cue paragraph becomes exactly the standalone line the parser expects."""
    root = safe_xml_fromstring(content)
    lines: list[str] = []
    for paragraph in root.iter("Paragraph"):
        text_parts = [node.text or "" for node in paragraph.findall("Text")]
        line = "".join(text_parts).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def extract_text(content: bytes, mime_type: str, filename: str) -> ExtractionResult:
    """Best-effort: a malformed/unsupported file never blocks the upload itself (the
    asset is still stored; see AssetService.upload_stream) -- it just leaves `error` set
    and `text` empty, so Script Intelligence fails later with a clear, specific message
    instead of the upload failing for a reason unrelated to storage."""
    try:
        if mime_type == "application/pdf":
            return ExtractionResult(text=_extract_pdf(content), extractor="pypdf")
        if mime_type == DOCX_MIME:
            return ExtractionResult(text=_extract_docx(content), extractor="python-docx")
        if mime_type == FDX_MIME:
            return ExtractionResult(text=_extract_fdx(content), extractor="fdx_xml")
    except Exception as exc:  # noqa: BLE001 -- extraction failure is data, not a bug
        return ExtractionResult(text="", extractor="none", error=f"{type(exc).__name__}: {exc}")
    return ExtractionResult(
        text="", extractor="none", error=f"No extractor registered for '{mime_type}' ('{filename}')."
    )
