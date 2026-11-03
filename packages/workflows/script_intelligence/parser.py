"""Screenplay parser extracting structured scenes and entities from script text."""

import re
from typing import Any, Dict, List, Tuple


class ScreenplayParser:
    """Robust screenplay parser for standard industry formatted scripts."""

    SCENE_HEADING_REGEX = re.compile(
        r"^(?P<setting>INT\./EXT\.|EXT\./INT\.|INT\.|EXT\.)\s+(?P<location>[^-]+?)(?:\s*-\s*(?P<time>[^\n]+))?$",
        re.IGNORECASE | re.MULTILINE,
    )
    CHARACTER_CUE_REGEX = re.compile(r"^[A-Z0-9\s\(\)\'\.\-]{2,30}$")

    def parse(self, text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse script text into raw scene dicts and entity candidate dicts."""
        lines = [line.strip() for line in text.splitlines()]
        scenes: List[Dict[str, Any]] = []
        entities: Dict[str, Dict[str, Any]] = {}

        current_scene: Dict[str, Any] | None = None
        current_scene_lines: List[str] = []
        current_characters: set = set()
        scene_counter = 0

        for line_idx, line in enumerate(lines):
            if not line:
                continue

            match = self.SCENE_HEADING_REGEX.match(line)
            if match:
                # Flush previous scene
                if current_scene:
                    current_scene["summary"] = self._generate_summary(current_scene_lines)
                    current_scene["characters_present"] = sorted(list(current_characters))
                    scenes.append(current_scene)

                scene_counter += 1
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

                # Register location entity
                loc_key = location.lower()
                if loc_key not in entities:
                    entities[loc_key] = {
                        "name": location,
                        "category": "location",
                        "description": f"Location featured in {setting} scenes",
                        "source_locator": f"Scene {scene_counter}",
                        "confidence": 0.98,
                    }
                continue

            # Check if line is a character dialogue cue (typically uppercase, centered or indented)
            if (
                line.isupper()
                and len(line) <= 30
                and not line.startswith("(")
                and not line.endswith(":")
                and not any(line.startswith(p) for p in ["CUT TO", "FADE", "DISSOLVE", "SMASH CUT"])
            ):
                char_name = re.sub(r"\(.*?\)", "", line).strip().title()
                if len(char_name) > 1:
                    current_characters.add(char_name)
                    char_key = char_name.lower()
                    if char_key not in entities:
                        entities[char_key] = {
                            "name": char_name,
                            "category": "character",
                            "description": f"Character speaking in Scene {scene_counter or 1}",
                            "source_locator": f"Line {line_idx + 1}",
                            "confidence": 0.95,
                        }
            else:
                current_scene_lines.append(line)

        # Flush final scene
        if current_scene:
            current_scene["summary"] = self._generate_summary(current_scene_lines)
            current_scene["characters_present"] = sorted(list(current_characters))
            scenes.append(current_scene)

        # Fallback if no standard sluglines were detected
        if not scenes and lines:
            scenes.append({
                "scene_number": 1,
                "heading": "SCENE 1 - GENERAL NARRATIVE",
                "setting": "INT",
                "location_name": "General Setting",
                "time_of_day": "DAY",
                "source_locator": "Text Start",
                "characters_present": sorted(list(current_characters)),
                "summary": " ".join(lines[:5]) if lines else "Script opening sequence.",
            })

        return scenes, list(entities.values())

    def _generate_summary(self, lines: List[str]) -> str:
        action_lines = [line for line in lines if not line.isupper() and len(line) > 10]
        if action_lines:
            summary = " ".join(action_lines[:3])
            return summary[:300] + ("..." if len(summary) > 300 else "")
        return "Scene action sequence."
