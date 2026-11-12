"""Deterministic Screenplay Suggestions engine (WF-15, D2 TFD-SCR-005).

Proposes creative suggestions across all 7 kinds (PRD §3 Workflow 2) -- it never edits
the screenplay itself, only proposes. Parameterized on the screenplay's own real,
parsed scene structure (packages.workflows.script_intelligence.parser.ScreenplayParser),
the same real input every other WF-01..04 generator reads from, not placeholder text.
"""

from __future__ import annotations

from typing import Any

from packages.workflows.script_intelligence.parser import ScreenplayParser

_SHORT_SCENE_WORD_THRESHOLD = 25
_LONG_SCENE_WORD_THRESHOLD = 180


class ScreenplaySuggester:
    """Proposes suggestions grounded in a screenplay version's own parsed scenes."""

    def __init__(self) -> None:
        self._parser = ScreenplayParser()

    def suggest(self, content_text: str, scope_notes: str | None = None) -> list[dict[str, Any]]:
        scenes, _entities = self._parser.parse(content_text)
        if not scenes:
            return []

        suggestions: list[dict[str, Any]] = []
        for i, scene in enumerate(scenes):
            anchor = f"Scene {scene['scene_number']}"
            word_count = len(scene["summary"].split())
            character_count = len(scene["characters_present"])

            if word_count <= _SHORT_SCENE_WORD_THRESHOLD:
                suggestions.append(
                    self._suggestion(
                        kind="pacing",
                        anchor=anchor,
                        text=f"{anchor} ({scene['heading']}) is very brief -- consider whether it earns its "
                        "own scene or should be folded into a neighbouring one for pacing.",
                        rationale=f"Only {word_count} words of description.",
                    )
                )
            elif word_count >= _LONG_SCENE_WORD_THRESHOLD:
                suggestions.append(
                    self._suggestion(
                        kind="dramatic_improvement",
                        anchor=anchor,
                        text=f"{anchor} ({scene['heading']}) runs long -- consider a mid-scene turn or "
                        "complication to sustain dramatic tension.",
                        rationale=f"{word_count} words of description, above the typical scene length.",
                    )
                )

            if character_count >= 2:
                suggestions.append(
                    self._suggestion(
                        kind="character_development",
                        anchor=anchor,
                        text=f"{anchor} features {', '.join(scene['characters_present'])} together -- "
                        "consider a beat that reveals a new facet of their relationship.",
                        rationale=f"{character_count} characters present in this scene.",
                    )
                )
            elif character_count == 1:
                suggestions.append(
                    self._suggestion(
                        kind="dialogue_improvement",
                        anchor=anchor,
                        text=f"{anchor} has a single character present -- an internal monologue or a brief "
                        "phone/voice-over exchange could add dialogue variety.",
                        rationale="Only one character present.",
                    )
                )

            if i + 1 < len(scenes):
                next_scene = scenes[i + 1]
                if scene["location_name"] == next_scene["location_name"] and scene["time_of_day"] == next_scene[
                    "time_of_day"
                ]:
                    suggestions.append(
                        self._suggestion(
                            kind="transition",
                            anchor=anchor,
                            text=f"{anchor} and Scene {next_scene['scene_number']} share the same location and "
                            "time of day -- consider merging them or varying the transition (match cut, time jump).",
                            rationale="Two consecutive scenes share location and time of day.",
                        )
                    )

        if len(scenes) >= 2:
            first, last = scenes[0], scenes[-1]
            suggestions.append(
                self._suggestion(
                    kind="storytelling_opportunity",
                    anchor=f"Scene {first['scene_number']}-{last['scene_number']}",
                    text=f"The arc from {first['heading']} to {last['heading']} could be bridged with a "
                    "short callback beat tying the opening image back in at the close.",
                    rationale="Structural suggestion spanning the full screenplay.",
                )
            )

        if scope_notes and scope_notes.strip():
            suggestions.append(
                self._suggestion(
                    kind="alternative_scene",
                    anchor=f"Scene {scenes[0]['scene_number']}",
                    text=f"Per the brief ('{scope_notes.strip()[:80]}'), consider an alternative opening "
                    "scene that establishes the same premise more directly.",
                    rationale="Director-provided scope note.",
                )
            )

        return suggestions

    @staticmethod
    def _suggestion(*, kind: str, anchor: str, text: str, rationale: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "anchor": anchor,
            "suggestion_text": text,
            "rationale": rationale,
            "confidence": 0.75,
        }
