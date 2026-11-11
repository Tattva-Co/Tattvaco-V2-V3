"""Real text extraction for PDF, DOCX and Final Draft (.fdx) -- C7.

Before this, these formats were accepted for upload but Script Intelligence refused them
outright (ScriptReviewService.load_script_text only supported text/*). These tests prove
extraction produces text the existing screenplay parser
(packages/workflows/script_intelligence/parser.py) can actually read: real sluglines and
character cues on their own lines, not raw/garbled bytes.
"""

from __future__ import annotations

import io

import docx
from pypdf import PdfReader, PdfWriter

from packages.services.extraction import extract_text
from packages.storage.magic_bytes import DOCX_MIME, FDX_MIME
from packages.workflows.script_intelligence.parser import ScreenplayParser

FDX_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="1">
  <Content>
    <Paragraph Type="Scene Heading"><Text>INT. WAR COUNCIL CHAMBER - NIGHT</Text></Paragraph>
    <Paragraph Type="Action"><Text>Torches flicker against ancient stone walls.</Text></Paragraph>
    <Paragraph Type="Character"><Text>BHAVANI</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>The northern pass is compromised.</Text></Paragraph>
  </Content>
</FinalDraft>
"""


def _make_pdf_bytes(lines: list[str]) -> bytes:
    """A real, valid single-page PDF containing the given lines as literal text, built
    with pypdf's low-level writer rather than an opaque fixture file, so the test
    documents exactly what should come back out. pypdf's PdfWriter has no text-drawing
    API, so this writes a minimal content stream directly (one `BT ... Tj ET` block per
    line, using the standard non-embedded Helvetica font) rather than pulling in a
    heavier PDF-generation dependency just for one test fixture."""
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    page = writer.pages[0]

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )

    y = 750
    ops = []
    for line in lines:
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        ops.append(f"BT /F1 12 Tf 72 {y} Td ({escaped}) Tj ET")
        y -= 20
    stream = DecodedStreamObject()
    stream.set_data("\n".join(ops).encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_docx_bytes(lines: list[str]) -> bytes:
    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


SCREENPLAY_LINES = [
    "INT. WAR COUNCIL CHAMBER - NIGHT",
    "Torches flicker against ancient stone walls.",
    "BHAVANI",
    "The northern pass is compromised.",
]


def test_extracts_docx_text_the_parser_can_read_as_a_real_scene():
    content = _make_docx_bytes(SCREENPLAY_LINES)
    result = extract_text(content, DOCX_MIME, "script.docx")

    assert result.error is None
    assert result.extractor == "python-docx"
    assert "INT. WAR COUNCIL CHAMBER - NIGHT" in result.text

    scenes, entities = ScreenplayParser().parse(result.text)
    assert len(scenes) == 1
    assert scenes[0]["heading"] == "INT. WAR COUNCIL CHAMBER - NIGHT"
    assert any(e["name"] == "Bhavani" for e in entities)


def test_extracts_fdx_text_the_parser_can_read_as_a_real_scene():
    result = extract_text(FDX_FIXTURE, FDX_MIME, "script.fdx")

    assert result.error is None
    assert result.extractor == "fdx_xml"
    assert "INT. WAR COUNCIL CHAMBER - NIGHT" in result.text

    scenes, entities = ScreenplayParser().parse(result.text)
    assert len(scenes) == 1
    assert scenes[0]["setting"] == "INT."
    assert any(e["name"] == "Bhavani" for e in entities)


def test_extracts_pdf_text():
    content = _make_pdf_bytes(["Hello from a real PDF page."])
    result = extract_text(content, "application/pdf", "doc.pdf")

    assert result.error is None
    assert result.extractor == "pypdf"
    assert "Hello from a real PDF page." in result.text
    # Cross-check with pypdf directly, so this test fails loudly if the fixture itself
    # (not extract_text) stops producing real extractable text.
    assert PdfReader(io.BytesIO(content)).pages[0].extract_text()


def test_malformed_pdf_reports_an_error_instead_of_raising():
    result = extract_text(b"not a real pdf", "application/pdf", "broken.pdf")
    assert result.text == ""
    assert result.error is not None


def test_malformed_fdx_reports_an_error_instead_of_raising():
    result = extract_text(b"<not><valid", FDX_MIME, "broken.fdx")
    assert result.text == ""
    assert result.error is not None


def test_unrecognised_mime_type_reports_a_clear_error():
    result = extract_text(b"whatever", "application/octet-stream", "mystery.bin")
    assert result.text == ""
    assert "No extractor registered" in result.error
