"""Golden screenplay set (TFD-STY-007): scene/character F1 and exact-match dialogue
preservation, measured against a recorded baseline, across every format Script
Intelligence actually supports (Fountain/plain-text, PDF, DOCX, Final Draft .fdx) and
including a non-uppercase (Fountain forced "@") character cue.

Run as part of the normal test suite (and so, already, in CI) -- "before any quality
claim" (TFD-STY-007) is satisfied by this test existing and passing, not by a separate
CI job; the parser is deterministic, so there is nothing a separate job would catch that
this test run does not already catch (DEC: see docs/audit/10 decision register).
"""

from __future__ import annotations

import io

import docx

from packages.services.extraction import extract_text
from packages.storage.magic_bytes import DOCX_MIME, FDX_MIME
from packages.workflows.script_intelligence.parser import ScreenplayParser

# A forced "@" cue (Priya) deliberately exercises the non-uppercase-cue requirement;
# everything else uses the standard all-uppercase convention.
GOLDEN_SCRIPT_LINES = [
    "EXT. HIMALAYAN PASS - DAWN",
    "",
    "Icy wind howls across the jagged mountain peaks.",
    "VIKRAM (40s), a weathered cartographer, adjusts his brass telescope.",
    "",
    "VIKRAM",
    "(quietly)",
    "The celestial alignment matches the scripture.",
    "",
    "INT. MONASTERY ARCHIVE - NIGHT",
    "",
    "Ancient scrolls line the floor-to-ceiling carved cedar shelves.",
    "",
    "@Priya",
    "The coordinates point to the sunken temple beneath the lake.",
    "",
    "EXT. SUNKEN TEMPLE - DAY",
    "",
    "Water drips from ancient stone archways.",
    "",
    "DEVA",
    "We have found it at last.",
]

EXPECTED_SCENE_HEADINGS = {
    "EXT. HIMALAYAN PASS - DAWN",
    "INT. MONASTERY ARCHIVE - NIGHT",
    "EXT. SUNKEN TEMPLE - DAY",
}
EXPECTED_CHARACTER_NAMES = {"Vikram", "Priya", "Deva"}
EXPECTED_DIALOGUE = [
    ("Vikram", "The celestial alignment matches the scripture."),
    ("Priya", "The coordinates point to the sunken temple beneath the lake."),
    ("Deva", "We have found it at last."),
]
EXPECTED_PARENTHETICALS = {("Vikram", "quietly")}

#: Recorded baseline (DEC, docs/audit/10 register): this golden set is small and
#: hand-crafted so the deterministic parser should extract it perfectly in every
#: format -- a regression below 1.0 on any metric fails the build.
BASELINE_SCENE_F1 = 1.0
BASELINE_CHARACTER_F1 = 1.0
BASELINE_DIALOGUE_EXACT_MATCH = 1.0


def _f1(predicted: set, expected: set) -> float:
    if not predicted and not expected:
        return 1.0
    if not predicted or not expected:
        return 0.0
    true_positives = len(predicted & expected)
    precision = true_positives / len(predicted)
    recall = true_positives / len(expected)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _score(text: str) -> dict[str, float]:
    scenes, entities, dialogue_segments = ScreenplayParser().parse(text)

    scene_f1 = _f1({s["heading"] for s in scenes}, EXPECTED_SCENE_HEADINGS)
    character_names = {e["name"] for e in entities if e["category"] == "character"}
    character_f1 = _f1(character_names, EXPECTED_CHARACTER_NAMES)

    actual_dialogue = {
        (d["character_name"], d["line_text"]) for d in dialogue_segments if d["line_text"]
    }
    exact_matches = sum(1 for pair in EXPECTED_DIALOGUE if pair in actual_dialogue)
    dialogue_exact_match = exact_matches / len(EXPECTED_DIALOGUE)

    actual_parentheticals = {
        (d["character_name"], d["parenthetical"]) for d in dialogue_segments if d["parenthetical"]
    }
    assert actual_parentheticals >= EXPECTED_PARENTHETICALS, (
        f"missing expected parentheticals: {EXPECTED_PARENTHETICALS - actual_parentheticals}"
    )

    return {
        "scene_f1": scene_f1,
        "character_f1": character_f1,
        "dialogue_exact_match": dialogue_exact_match,
    }


def _assert_meets_baseline(scores: dict[str, float], label: str) -> None:
    assert scores["scene_f1"] >= BASELINE_SCENE_F1, f"{label}: scene F1 regressed to {scores['scene_f1']}"
    assert scores["character_f1"] >= BASELINE_CHARACTER_F1, (
        f"{label}: character F1 regressed to {scores['character_f1']}"
    )
    assert scores["dialogue_exact_match"] >= BASELINE_DIALOGUE_EXACT_MATCH, (
        f"{label}: dialogue exact-match regressed to {scores['dialogue_exact_match']}"
    )


def test_golden_set_fountain_plain_text():
    text = "\n".join(GOLDEN_SCRIPT_LINES)
    _assert_meets_baseline(_score(text), "fountain")


def test_golden_set_docx():
    document = docx.Document()
    for line in GOLDEN_SCRIPT_LINES:
        document.add_paragraph(line)
    buf = io.BytesIO()
    document.save(buf)
    result = extract_text(buf.getvalue(), DOCX_MIME, "golden.docx")
    assert result.error is None
    _assert_meets_baseline(_score(result.text), "docx")


def test_golden_set_pdf():
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=1000)
    page = writer.pages[0]
    font_ref = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    y = 950
    ops = []
    for line in GOLDEN_SCRIPT_LINES:
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        ops.append(f"BT /F1 12 Tf 72 {y} Td ({escaped}) Tj ET")
        y -= 20
    stream = DecodedStreamObject()
    stream.set_data("\n".join(ops).encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    buf = io.BytesIO()
    writer.write(buf)

    result = extract_text(buf.getvalue(), "application/pdf", "golden.pdf")
    assert result.error is None
    _assert_meets_baseline(_score(result.text), "pdf")


def _fdx_paragraph_type(line: str) -> str:
    if line.startswith(("INT.", "EXT.")):
        return "Scene Heading"
    if line.startswith("@") or (line.isupper() and len(line) <= 30):
        return "Character"
    if line.startswith("("):
        return "Parenthetical"
    return "Action"


def test_golden_set_fdx():
    paragraphs = "\n".join(
        f'    <Paragraph Type="{_fdx_paragraph_type(line)}"><Text>{line}</Text></Paragraph>'
        for line in GOLDEN_SCRIPT_LINES
        if line
    )
    fdx = f"""<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="1">
  <Content>
{paragraphs}
  </Content>
</FinalDraft>
""".encode()

    result = extract_text(fdx, FDX_MIME, "golden.fdx")
    assert result.error is None
    _assert_meets_baseline(_score(result.text), "fdx")
