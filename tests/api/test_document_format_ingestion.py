"""End-to-end proof that PDF, DOCX and Final Draft (.fdx) screenplays are now real,
usable Script Intelligence inputs (C7) -- not just upload-allowed-but-unusable, which was
the state of the world before this milestone's text extraction
(packages/services/extraction.py) and ScriptReviewService.load_script_text update.
"""

from __future__ import annotations

import io

import docx

from tests.support import as_actor, create_project

SCREENPLAY_LINES = [
    "INT. WAR COUNCIL CHAMBER - NIGHT",
    "Torches flicker against ancient stone walls.",
    "BHAVANI",
    "The northern pass is compromised.",
]

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


def _docx_bytes(lines: list[str]) -> bytes:
    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def _pdf_bytes(lines: list[str]) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
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


def _run_script_intelligence_on(client, tenant, project_id, filename, content, mime):
    headers = as_actor(tenant.user_id)
    upload = client.post(
        f"/api/v1/projects/{project_id}/assets/upload",
        files={"file": (filename, io.BytesIO(content), mime)},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["mime_type"] == mime

    # Scanned clean synchronously (NoOpScanner): usable for a workflow in the very next
    # request, no waiting required.
    asset = client.get(f"/api/v1/projects/{project_id}/assets", headers=headers).json()[0]
    assert asset["scan_status"] == "clean"

    trigger = client.post(
        f"/api/v1/projects/{project_id}/workflows/script-intelligence",
        json={"script_asset_id": upload.json()["asset_id"], "sync_execution": True},
        headers=headers,
    )
    assert trigger.status_code == 200, trigger.text
    return trigger.json()


def test_a_pdf_screenplay_is_parsed_into_real_scene_candidates(client, tenant):
    project = create_project(client, tenant)
    workflow = _run_script_intelligence_on(
        client, tenant, project["id"], "script.pdf", _pdf_bytes(SCREENPLAY_LINES), "application/pdf"
    )
    assert workflow["candidate_summary"]["scene_count"] == 1

    headers = as_actor(tenant.user_id)
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    assert candidates["scenes"][0]["heading"] == "INT. WAR COUNCIL CHAMBER - NIGHT"


def test_a_docx_screenplay_is_parsed_into_real_scene_candidates(client, tenant):
    project = create_project(client, tenant)
    workflow = _run_script_intelligence_on(
        client,
        tenant,
        project["id"],
        "script.docx",
        _docx_bytes(SCREENPLAY_LINES),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert workflow["candidate_summary"]["scene_count"] == 1

    headers = as_actor(tenant.user_id)
    candidates = client.get(f"/api/v1/projects/{project['id']}/candidates", headers=headers).json()
    assert candidates["entities"]
    assert any(e["name"] == "Bhavani" for e in candidates["entities"])


def test_an_fdx_screenplay_is_parsed_into_real_scene_candidates(client, tenant):
    project = create_project(client, tenant)
    workflow = _run_script_intelligence_on(
        client, tenant, project["id"], "script.fdx", FDX_FIXTURE, "application/x-final-draft"
    )
    assert workflow["candidate_summary"]["scene_count"] == 1


def test_a_corrupt_pdf_fails_extraction_with_a_specific_message_not_a_crash(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    upload = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        # A valid %PDF- signature (passes magic-byte validation) but not a real,
        # parseable PDF structure -- extraction should fail gracefully at upload time,
        # and Script Intelligence should then report a clear, specific reason.
        files={"file": ("broken.pdf", io.BytesIO(b"%PDF-1.4\nnot a real pdf body"), "application/pdf")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text

    trigger = client.post(
        f"/api/v1/projects/{project['id']}/workflows/script-intelligence",
        json={"script_asset_id": upload.json()["asset_id"], "sync_execution": True},
        headers=headers,
    )
    assert trigger.status_code == 422, trigger.text
    assert "Could not extract text" in trigger.json()["detail"]


def test_upload_rejects_a_file_whose_bytes_do_not_match_its_declared_type(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/assets/upload",
        files={"file": ("fake.pdf", io.BytesIO(b"This is plain text, not a PDF."), "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 415, resp.text
    assert resp.json()["error"] == "UnsupportedMediaTypeError"
