"""Validates packages/domain/journey_manifest.yaml (S0.3, spec: docs/product/JOURNEY_MANIFEST.md).

Drift guards against the sources the manifest is built from:
- Guided Workspace Wireframe v1.1 (`stages` data): section/group order, titles, purposes,
  completion rules and screen coverage;
- PRD v1.0: every linked TFD requirement exists;
- Information Architecture v1.1: the Studio Tools catalogue matches the canonical S- screens;
- packages/domain/capabilities.py: every capability key exists.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from packages.domain.capabilities import CAPABILITY_KEYS

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "packages/domain/journey_manifest.yaml"
SPEC = ROOT / "docs/product/JOURNEY_MANIFEST.md"
PRD = ROOT / "docs/product/PRD_v1.0.md"
IA = ROOT / "docs/product/INFORMATION_ARCHITECTURE.md"
WIREFRAME = (
    ROOT
    / "docs/product/ux/guided-workspace-v1.0/Tattva_AI_Film_Director_Guided_Workspace_Wireframe_v1.1.html"
)

GROUP_ID = re.compile(r"^JRN-(\d{2})\.(\d+)$")
SUPPORTED_CONDITIONS = {"shot_method_in"}
SHOT_METHODS = {
    "fully_ai_generated",
    "live_action_chroma",
    "performance_transformation",
    "digital_human",
    "combined",
}
SYSTEM_CHECK_KEYS = {
    "screenplay_asset_present",
    "research_questions_present",
    "workflow_completed:script_intelligence",
    "no_pending_candidates:script_intelligence",
    "no_pending_candidates:historical_research",
    "no_pending_candidates:storyboard_intelligence",
    "approved_rules_present:film_bible",
}
DEFERRED_SCREENS = {"S-APR-04"}


def _norm(text: str) -> str:
    return " ".join(text.split())


@lru_cache
def manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


@lru_cache
def wireframe_stages() -> list[dict]:
    html = WIREFRAME.read_text(encoding="utf-8")
    start = html.index("const stages=") + len("const stages=")
    stages, _ = json.JSONDecoder().raw_decode(html[start:])
    return stages


def groups() -> list[dict]:
    return [g for s in manifest()["sections"] for g in s["groups"]]


def test_sections_and_groups_match_wireframe_v1_1() -> None:
    sections = manifest()["sections"]
    stages = wireframe_stages()
    assert [s["id"] for s in sections] == [f"JRN-{st['id']}" for st in stages]
    for section, stage in zip(sections, stages, strict=True):
        assert section["title"] == stage["title"]
        assert [g["id"] for g in section["groups"]] == [f"JRN-{it['id']}" for it in stage["items"]]
        for group, item in zip(section["groups"], stage["items"], strict=True):
            assert group["title"] == item["title"], group["id"]
            assert _norm(group["purpose"]) == _norm(item["description"]), group["id"]
            assert _norm(group["completion_rule"]) == _norm(item["completion"]), group["id"]
            assert group["required"] is item["required"], group["id"]
    assert len(groups()) == 70


def test_ids_are_unique_and_well_formed() -> None:
    ids = [g["id"] for g in groups()]
    assert len(ids) == len(set(ids))
    for section in manifest()["sections"]:
        for group in section["groups"]:
            m = GROUP_ID.match(group["id"])
            assert m, group["id"]
            assert section["id"] == f"JRN-{m.group(1)}", group["id"]
    suffixes = [p["suffix"] for p in manifest()["subpoint_template"]]
    assert suffixes == sorted(set(suffixes)), "subpoint suffixes must be unique and ordered"


def test_enumerated_fields_are_valid() -> None:
    enums = manifest()["enums"]
    for g in groups():
        assert g["release"] in enums["releases"], g["id"]
        assert g["na"] in enums["na_policies"], g["id"]
        assert g["completion_check"]["kind"] in enums["completion_check_kinds"], g["id"]
        if g["completion_check"]["kind"] == "system":
            assert g["completion_check"]["key"] in SYSTEM_CHECK_KEYS, g["id"]
        app = g["applicability"]
        assert set(app) <= {"modes", "unless_any"}, g["id"]
        assert app["modes"] == "all" or set(app["modes"]) <= set(enums["production_modes"]), g["id"]
        for cond in app.get("unless_any", []):
            ((name, value),) = cond.items()
            assert name in SUPPORTED_CONDITIONS, g["id"]
            assert set(value) <= SHOT_METHODS, g["id"]


def test_capabilities_exist() -> None:
    for g in groups():
        assert g["act_capability"] in CAPABILITY_KEYS, g["id"]
        assert g["approval_capability"] is None or g["approval_capability"] in CAPABILITY_KEYS, g["id"]


def test_requirements_exist_in_prd() -> None:
    known = set(re.findall(r"^\| (TFD-[A-Z]+-\d{3}) \|", PRD.read_text(encoding="utf-8"), re.M))
    for g in groups():
        assert g["requirements"], g["id"]
        missing = set(g["requirements"]) - known
        assert not missing, f"{g['id']}: unknown requirements {missing}"


def test_studio_tools_catalogue_matches_ia() -> None:
    catalogue = manifest()["studio_tools"]
    ids = [t["id"] for t in catalogue]
    assert len(ids) == len(set(ids))
    ia_screens = set(re.findall(r"\bS-[A-Z]+-\d{2}\b", IA.read_text(encoding="utf-8")))
    assert set(ids) == ia_screens - DEFERRED_SCREENS
    section_ids = {s["id"] for s in manifest()["sections"]}
    releases = set(manifest()["enums"]["releases"])
    for tool in catalogue:
        assert tool["home"] in section_ids | {"workspace", "cross_stage"}, tool["id"]
        assert tool["release"] in releases, tool["id"]
    for g in groups():
        assert set(g["studio_tools"]) <= set(ids), g["id"]


def test_every_wireframe_screen_is_mapped() -> None:
    mapped = {n for t in manifest()["studio_tools"] for n in t["wireframe"]}
    assert mapped == set(range(1, 37))


def test_every_section_ships_something_in_fd_v1() -> None:
    for section in manifest()["sections"]:
        assert any(g["release"] in {"v1", "v1_v2"} for g in section["groups"]), section["id"]


@pytest.mark.parametrize("group_id", [g["id"] for g in groups()])
def test_spec_lists_every_group(group_id: str) -> None:
    assert f"`{group_id}`" in SPEC.read_text(encoding="utf-8")
