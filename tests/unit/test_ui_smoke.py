"""Render every Streamlit screen against a faked API to catch UI regressions."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from apps.ui import api_client
from apps.ui.api_client import ApiError
from apps.ui.views import NAVIGATION

APP_PATH = str(Path(__file__).resolve().parents[2] / "apps" / "ui" / "app.py")

PROJECT = {
    "id": "p1",
    "organization_id": "o1",
    "title": "Fort Film",
    "logline": "A siege.",
    "genre": "Historical Epic",
    "status": "active",
    "current_version": 2,
    "created_by": "u1",
    "created_at": "2026-11-01T00:00:00Z",
    "updated_at": "2026-11-01T00:00:00Z",
}
SCENE_CANDIDATE = {
    "id": "sc1", "workflow_run_id": "r1", "scene_number": 1, "heading": "EXT. FORT - DAY",
    "setting": "EXT.", "location_name": "Fort", "time_of_day": "DAY", "summary": "Dust.",
    "characters_present": ["Veer"], "status": "proposed",
}
ENTITY_CANDIDATE = {
    "id": "ec1", "workflow_run_id": "r1", "name": "Veer", "category": "character",
    "description": "Lead", "confidence": 0.95, "status": "proposed",
}
FAKE_RESPONSES = {
    "/projects": [PROJECT],
    "/projects/p1": PROJECT,
    "/projects/p1/assets": [
        {"id": "a1", "filename": "s.fountain", "size_bytes": 10, "checksum_sha256": "abc",
         "storage_path": "o1/p1/abc_s.fountain", "created_at": "2026-11-01T00:00:00Z"}
    ],
    "/projects/p1/scenes": [
        {**SCENE_CANDIDATE, "id": "s1", "source_locator": "Scene 1", "project_version": 2}
    ],
    "/projects/p1/entities": [
        {"id": "e1", "name": "Veer", "category": "character", "description": None,
         "source_locator": "Line 3", "project_version": 2}
    ],
    "/projects/p1/versions": [
        {"version_number": 2, "branch_name": "main", "created_at": "x", "commit_message": "m", "snapshot_data": {}}
    ],
    "/projects/p1/audit-log": [
        {"action": "project_created", "target_type": "project", "target_id": "p1-xxxxxxxx",
         "actor_id": "u1", "created_at": "x", "details": {}}
    ],
    "/projects/p1/candidates": {
        "scenes": [SCENE_CANDIDATE],
        "entities": [ENTITY_CANDIDATE],
        "research_claims": [],
        "research_questions": [],
        "approvals": [{"id": "ap1", "workflow_run_id": "r1", "scope": "s", "status": "pending", "candidate_summary": {}}],
    },
    "/projects/p1/research/questions": [
        {"id": "rq1", "project_id": "p1", "project_version": 2, "text": "Armor?", "category": "military", "status": "open", "created_at": "x", "updated_at": "x"}
    ],
    "/projects/p1/research/sources": [
        {"id": "rs1", "project_id": "p1", "project_version": 2, "title": "History", "tier": "tier_1_primary", "author": "A", "publication_year": 2000, "locator": "p.1", "url": None, "asset_id": None, "reliability_notes": None, "created_at": "x"}
    ],
    "/projects/p1/research/claims": [
        {"id": "rc1", "project_id": "p1", "project_version": 2, "claim_class": "historical_fact", "statement": "Fact", "era_or_date": "200 BCE", "location": "Kalinga", "confidence": 0.9, "source_id": "rs1", "question_id": None, "status": "approved", "created_at": "x"}
    ],
    "/projects/p1/research/conflicts": [],
}


@pytest.fixture
def fake_api(monkeypatch):
    calls = []

    def fake_request(self, method, endpoint, **kwargs):
        calls.append((method, endpoint, kwargs))
        if endpoint in FAKE_RESPONSES:
            return FAKE_RESPONSES[endpoint]
        raise ApiError(f"unexpected {method} {endpoint}", 404)

    monkeypatch.setattr(api_client.TattvaApiClient, "_request", fake_request)
    return calls


@pytest.mark.parametrize("screen", list(NAVIGATION))
def test_every_screen_renders_without_errors(fake_api, screen):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    at.sidebar.radio[0].set_value(screen).run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]


def test_review_screen_lists_only_candidates_of_its_run(fake_api):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    at.sidebar.radio[0].set_value("🔍 Candidate Review & Approvals").run()
    labels = [cb.label for cb in at.checkbox]
    assert labels == [
        "Scene 1: EXT. FORT - DAY (EXT. / DAY)",
        "[CHARACTER] Veer (Confidence: 95%)",
    ]


def test_api_errors_are_shown_not_raised(monkeypatch):
    def failing(self, method, endpoint, **kwargs):
        raise ApiError("Cannot reach the Tattva API", None)

    monkeypatch.setattr(api_client.TattvaApiClient, "_request", failing)
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert not at.exception
    assert any("Cannot reach the Tattva API" in e.value for e in at.error)
