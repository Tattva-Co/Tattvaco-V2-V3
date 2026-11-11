"""Golden-set eval harness for the ModelGateway (C10, packages/ai/gateway.py).

One small, real, runnable fixture per capability. These assert two things
``DeterministicModelGateway`` must keep true regardless of how its generators evolve:
schema-valid output grounded in the given input, and determinism (same input -> same
output). A future LLM-backed ``ModelGateway`` implementation is not held to determinism,
but is held to the same fixtures and the same grounding assertions, loosened from
exact-match to semantic checks.
"""

from __future__ import annotations

from packages.ai.gateway import GENERATOR_MODE_DETERMINISTIC, DeterministicModelGateway

SAMPLE_SCREENPLAY = """
EXT. HIMALAYAN PASS - DAWN

Icy wind howls across the jagged mountain peaks.
VIKRAM (40s), a weathered cartographer, adjusts his brass telescope.

VIKRAM
The celestial alignment matches the scripture.

INT. MONASTERY ARCHIVE - NIGHT

Ancient scrolls line the floor-to-ceiling carved cedar shelves.
PRIYA (30s) illuminates a centuries-old mandala with an oil lamp.

PRIYA
The coordinates point to the sunken temple beneath the lake.
"""

GOLDEN_SCENES = [
    {
        "scene_number": 1,
        "heading": "EXT. HIMALAYAN PASS - DAWN",
        "setting": "EXT.",
        "location_name": "Himalayan Pass",
        "summary": "Icy wind howls across the jagged mountain peaks.",
        "characters_present": ["Vikram"],
    },
    {
        "scene_number": 2,
        "heading": "INT. MONASTERY ARCHIVE - NIGHT",
        "setting": "INT.",
        "location_name": "Monastery Archive",
        "summary": "Ancient scrolls line the floor-to-ceiling carved cedar shelves.",
        "characters_present": ["Priya"],
    },
]

GOLDEN_CLAIMS = [
    {
        "id": "claim-1",
        "claim_class": "historical_fact",
        "statement": "The Kalinga War occurred in 261 BCE.",
        "era_or_date": "261 BCE",
        "location": "Kalinga",
    },
]


def _gateway() -> DeterministicModelGateway:
    return DeterministicModelGateway()


def test_the_gateway_reports_its_mode():
    assert _gateway().mode == GENERATOR_MODE_DETERMINISTIC


def test_parse_screenplay_extracts_both_scenes_and_both_named_characters():
    result = _gateway().parse_screenplay(SAMPLE_SCREENPLAY)
    assert [s.heading for s in result.scenes] == [
        "EXT. HIMALAYAN PASS - DAWN",
        "INT. MONASTERY ARCHIVE - NIGHT",
    ]
    assert {"Vikram", "Priya"} <= {e.name for e in result.entities}


def test_parse_screenplay_is_deterministic():
    gateway = _gateway()
    first = gateway.parse_screenplay(SAMPLE_SCREENPLAY)
    second = gateway.parse_screenplay(SAMPLE_SCREENPLAY)
    assert first.model_dump() == second.model_dump()


def test_investigate_history_returns_claims_grounded_in_the_named_topic():
    result = _gateway().investigate_history("The Kalinga War", None)
    assert result.claims
    assert any("kalinga" in (c.location or "").lower() for c in result.claims)
    assert result.questions


def test_investigate_history_is_deterministic():
    gateway = _gateway()
    first = gateway.investigate_history("The Kalinga War", None)
    second = gateway.investigate_history("The Kalinga War", None)
    assert first.model_dump() == second.model_dump()


def test_align_storyboard_produces_panels_tied_to_the_given_scenes():
    result = _gateway().align_storyboard(GOLDEN_SCENES, brief=None)
    assert result.panels
    assert {p.suggested_scene_number for p in result.panels} <= {1, 2}


def test_align_storyboard_is_deterministic():
    gateway = _gateway()
    first = gateway.align_storyboard(GOLDEN_SCENES, brief=None)
    second = gateway.align_storyboard(GOLDEN_SCENES, brief=None)
    assert first.model_dump() == second.model_dump()


def test_synthesize_film_bible_grounds_rules_in_supplied_user_notes():
    result = _gateway().synthesize_film_bible(GOLDEN_SCENES, GOLDEN_CLAIMS, user_notes="Keep the palette warm")
    assert result.rules
    assert any("warm" in (r.rule_text or "").lower() for r in result.rules)


def test_synthesize_film_bible_is_deterministic():
    gateway = _gateway()
    first = gateway.synthesize_film_bible(GOLDEN_SCENES, GOLDEN_CLAIMS, user_notes="Keep the palette warm")
    second = gateway.synthesize_film_bible(GOLDEN_SCENES, GOLDEN_CLAIMS, user_notes="Keep the palette warm")
    assert first.model_dump() == second.model_dump()
