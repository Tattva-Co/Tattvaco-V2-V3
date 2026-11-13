"""Screenplay parser extracting structured scenes, entities and dialogue from script
text (D3, TFD-STY-002/003/007: verbatim dialogue segments, non-uppercase cues)."""

import re
from typing import Any, Dict, List, Tuple

#: Fountain's own convention for forcing a Character element whose cue is not
#: uppercase: a leading "@" (https://fountain.io, "Character" section). Lets a real
#: mixed-case cue like "@Ashoka" be recognised without guessing at capitalisation
#: heuristics of our own.
FORCED_CUE_PREFIX = "@"
_NON_CUE_PREFIXES = ("CUT TO", "FADE", "DISSOLVE", "SMASH CUT")


class ScreenplayParser:
    """Robust screenplay parser for standard industry formatted scripts."""

    SCENE_HEADING_REGEX = re.compile(
        r"^(?P<setting>INT\./EXT\.|EXT\./INT\.|INT\.|EXT\.)\s+(?P<location>[^-]+?)(?:\s*-\s*(?P<time>[^\n]+))?$",
        re.IGNORECASE | re.MULTILINE,
    )
    CHARACTER_CUE_REGEX = re.compile(r"^[A-Z0-9\s\(\)\'\.\-]{2,30}$")

    def parse(self, text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse script text into raw scene dicts, entity candidate dicts, and verbatim
        dialogue segment dicts (one per spoken/parenthetical line)."""
        lines = [line.strip() for line in text.splitlines()]
        scenes: List[Dict[str, Any]] = []
        entities: Dict[str, Dict[str, Any]] = {}
        dialogue_segments: List[Dict[str, Any]] = []

        current_scene: Dict[str, Any] | None = None
        current_scene_lines: List[str] = []
        current_characters: set = set()
        scene_counter = 0
        dialogue_order = 0
        active_speaker: str | None = None

        def flush_scene() -> None:
            if current_scene:
                current_scene["summary"] = self._generate_summary(current_scene_lines)
                current_scene["characters_present"] = sorted(current_characters)
                scenes.append(current_scene)

        for line_idx, line in enumerate(lines):
            if not line:
                active_speaker = None  # a blank line always ends a dialogue block
                continue

            match = self.SCENE_HEADING_REGEX.match(line)
            if match:
                flush_scene()

                scene_counter += 1
                dialogue_order = 0
                active_speaker = None
                setting = match.group("setting").upper()
                location = match.group("location").strip().title()
                time_of_day = (match.group("time") or "DAY").strip().upper()

                current_scene = {
                    "scene_number": scene_counter,
                    "heading": line,
                    "setting": setting,
                    "location_name": location,
                    "time_of_day": time_of_day,
                    "source_locator": f"Scene {scene_counter} (Line {line_idx + 1})",
                    "characters_present": [],
                    "summary": "",
                }
                current_scene_lines = []
                current_characters = set()

                # Register location entity (TFD-STY-003: resolved at promotion time).
                loc_key = location.lower()
                if loc_key not in entities:
                    entities[loc_key] = {
                        "name": location,
                        "category": "location",
                        "description": f"Location featured in {setting} scenes",
                        "source_locator": f"Scene {scene_counter}",
                        "confidence": 0.98,
                        "aliases": [location],
                    }
                continue

            cue_name = self._match_character_cue(line)
            if cue_name is not None:
                current_characters.add(cue_name)
                char_key = cue_name.lower()
                if char_key not in entities:
                    entities[char_key] = {
                        "name": cue_name,
                        "category": "character",
                        "description": f"Character speaking in Scene {scene_counter or 1}",
                        "source_locator": f"Line {line_idx + 1}",
                        "confidence": 0.95,
                        "aliases": [cue_name],
                    }
                elif cue_name not in entities[char_key]["aliases"]:
                    entities[char_key]["aliases"].append(cue_name)
                active_speaker = cue_name
                continue

            if active_speaker is not None:
                # TFD-STY-002: verbatim -- the line is stored exactly as encountered
                # (only the same leading/trailing-whitespace strip every other line
                # already gets), never reformatted or summarised.
                is_parenthetical = line.startswith("(") and line.endswith(")")
                dialogue_order += 1
                dialogue_segments.append(
                    {
                        "scene_number": scene_counter or 1,
                        "character_name": active_speaker,
                        "line_text": "" if is_parenthetical else line,
                        "parenthetical": line[1:-1].strip() if is_parenthetical else None,
                        "order_in_scene": dialogue_order,
                        "source_locator": f"Scene {scene_counter or 1} (Line {line_idx + 1})",
                    }
                )
                continue

            current_scene_lines.append(line)

        flush_scene()

        # Fallback if no standard sluglines were detected
        if not scenes and lines:
            scenes.append({
                "scene_number": 1,
                "heading": "SCENE 1 - GENERAL NARRATIVE",
                "setting": "INT",
                "location_name": "General Setting",
                "time_of_day": "DAY",
                "source_locator": "Text Start",
                "characters_present": sorted(current_characters),
                "summary": " ".join(lines[:5]) if lines else "Script opening sequence.",
            })

        return scenes, list(entities.values()), dialogue_segments

    def _match_character_cue(self, line: str) -> str | None:
        """Returns the resolved (title-cased, parenthetical-stripped) character name if
        ``line`` is a character cue, else None. Two forms: the standard all-uppercase
        cue, or a Fountain forced cue (a leading "@") for a non-uppercase name
        (TFD-STY-002/AT-STY-003.1)."""
        if any(line.startswith(p) for p in _NON_CUE_PREFIXES):
            return None

        if line.startswith(FORCED_CUE_PREFIX):
            raw = line[len(FORCED_CUE_PREFIX):].strip()
        elif line.isupper() and len(line) <= 30 and not line.startswith("(") and not line.endswith(":"):
            raw = line
        else:
            return None

        name = re.sub(r"\(.*?\)", "", raw).strip().title()
        return name if len(name) > 1 else None

    def _generate_summary(self, lines: List[str]) -> str:
        action_lines = [line for line in lines if not line.isupper() and len(line) > 10]
        if action_lines:
            summary = " ".join(action_lines[:3])
            return summary[:300] + ("..." if len(summary) > 300 else "")
        return "Scene action sequence."
