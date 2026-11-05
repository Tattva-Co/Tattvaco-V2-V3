"""Deterministic Storyboard Intelligence aligner / panel generator.

Converts scene descriptions, screenplay context, or director prompts into
structured visual storyboard panel candidates with shot types, visual notes,
and scene alignment locators.
"""

from __future__ import annotations

from typing import Any


class StoryboardAligner:
    """Generates visual panel candidates and aligns them with scene chronology."""

    def generate_panels(
        self,
        scenes: list[dict[str, Any]],
        brief: str | None = None,
    ) -> list[dict[str, Any]]:
        panels: list[dict[str, Any]] = []
        panel_counter = 1

        if not scenes:
            # Generate generic sequence panels from brief or title
            default_shots = [
                ("establishing", "Extreme wide establishing vista introducing the geographic environment."),
                ("wide", "Full view of key figures assembling on the terrain."),
                ("medium", "Medium tracking shot following character movement and tactical interaction."),
                ("close_up", "Tense character facial expression emphasizing emotional stakes."),
            ]
            for shot_type, desc in default_shots:
                panels.append({
                    "panel_number": panel_counter,
                    "suggested_scene_number": 1,
                    "shot_type": shot_type,
                    "description": desc,
                    "visual_notes": "Natural atmospheric dawn haze; high contrast side lighting.",
                    "dialogue_snippet": None,
                    "confidence": 0.85,
                })
                panel_counter += 1
            return panels

        for s in scenes:
            s_num = s.get("scene_number", 1)
            heading = s.get("heading", f"SCENE {s_num}")
            summary = s.get("summary", "")
            chars = s.get("characters_present", [])

            # 1. Establishing Shot
            panels.append({
                "panel_number": panel_counter,
                "suggested_scene_number": s_num,
                "shot_type": "establishing" if "EXT" in heading.upper() else "wide",
                "description": f"Establishing angle on {heading}. {summary[:150]}",
                "visual_notes": f"Spatial context for Scene {s_num}; deep focus lens; setting: {s.get('setting', 'EXT.')}.",
                "dialogue_snippet": None,
                "confidence": 0.95,
            })
            panel_counter += 1

            # 2. Medium Shot with Characters
            char_text = f"focusing on {', '.join(chars)}" if chars else "character interaction"
            panels.append({
                "panel_number": panel_counter,
                "suggested_scene_number": s_num,
                "shot_type": "medium",
                "description": f"Medium shot in {heading}, {char_text}.",
                "visual_notes": "Eye-level camera; 50mm lens; standard coverage.",
                "dialogue_snippet": f"Action beat in Scene {s_num}",
                "confidence": 0.90,
            })
            panel_counter += 1

            # 3. Close-up or dynamic angle if character present
            if chars:
                panels.append({
                    "panel_number": panel_counter,
                    "suggested_scene_number": s_num,
                    "shot_type": "close_up",
                    "description": f"Close-up portrait of {chars[0]} reacting to unfolding tension.",
                    "visual_notes": "Shallow depth of field; 85mm prime lens; emotional focus.",
                    "dialogue_snippet": f"Key dialogue cue for {chars[0]}",
                    "confidence": 0.92,
                })
                panel_counter += 1

        return panels

