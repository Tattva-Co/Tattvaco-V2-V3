"""Film Bible visual-world rule synthesizer (Workflow G-04, Tasks T-48, T-50).

Synthesizes structured aesthetic rules, color palettes, lighting atmosphere,
architectural environments, material culture, and camera language from approved
scenes and historical research claims.
"""

from __future__ import annotations

from typing import Any, Sequence

from packages.workflows.film_bible_synthesis.conflict_detector import RuleConflictDetector


class FilmBibleSynthesizer:
    def __init__(self) -> None:
        self.detector = RuleConflictDetector()

    def synthesize_rules(
        self,
        scenes: Sequence[dict[str, Any]],
        claims: Sequence[dict[str, Any]],
        user_notes: str | None = None,
    ) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []

        # 1. Tone & Aesthetic
        tone_rule = {
            "category": "tone_aesthetic",
            "title": "Grounded Historical Realism & Atmospheric Texture",
            "rule_text": (
                "Visually grounded historical realism. Prioritize tactile surfaces, natural dust, "
                "patina on metals, and weathered textures. Avoid polished CGI sheen or hyper-stylized saturated fantasy."
            ),
            "negative_prompt_guidance": "cgi render, plastic sheen, glowing aura, hyper-saturated fantasy, synthetic polish, modern cinematic bloom",
            "strictness": "mandatory",
            "suggested_claim_statement": None,
            "confidence": 0.95,
        }
        res = self.detector.check_rule(tone_rule["rule_text"], tone_rule["category"], claims)
        tone_rule["conflict_warning"] = res.warning_text
        rules.append(tone_rule)

        # 2. Color Palette
        # Extract location/era cues if present
        color_rule = {
            "category": "color_palette",
            "title": "Earthy Terracotta, Ochre & Weathered Bronze",
            "rule_text": (
                "Dominant palette anchored in terracotta reds, unbleached cotton off-white, yellow ochre, "
                "and deep river silt grey. Accent colors restricted to natural plant and mineral dyes: madder red and indigo."
            ),
            "negative_prompt_guidance": "neon colors, synthetic aniline dyes, chemical purple, bright magenta, electric cyan",
            "strictness": "mandatory",
            "suggested_claim_statement": claims[0]["statement"] if claims else None,
            "confidence": 0.92,
        }
        res = self.detector.check_rule(color_rule["rule_text"], color_rule["category"], claims)
        color_rule["conflict_warning"] = res.warning_text
        rules.append(color_rule)

        # 3. Lighting & Atmosphere
        lighting_rule = {
            "category": "lighting_atmosphere",
            "title": "Low-Raking Sun & High-Contrast Torchlight",
            "rule_text": (
                "Natural directional illumination. Exterior scenes feature low-raking dawn or dusk sunlight "
                "penetrating atmospheric haze. Interior night scenes lit solely by open earthen oil lamps and torches with deep amber falloff."
            ),
            "negative_prompt_guidance": "flat studio lighting, neon rim light, diffuse led backlight, softbox lighting",
            "strictness": "guideline",
            "suggested_claim_statement": None,
            "confidence": 0.88,
        }
        res = self.detector.check_rule(lighting_rule["rule_text"], lighting_rule["category"], claims)
        lighting_rule["conflict_warning"] = res.warning_text
        rules.append(lighting_rule)

        # 4. Architectural Environment
        arch_statement = None
        for c in claims:
            if "rampart" in c.get("statement", "").lower() or "brick" in c.get("statement", "").lower() or "fort" in c.get("statement", "").lower():
                arch_statement = c.get("statement")
                break

        arch_text = (
            "Fortifications constructed from dressed laterite blocks and sun-dried mudbrick with defensive clay glacis. "
            "Civic buildings feature heavy timber posts, bamboo lattices, and terracotta tiled roofs."
        )
        arch_rule = {
            "category": "architectural_environment",
            "title": "Laterite Masonry, Mudbrick Ramparts & Timber Framing",
            "rule_text": arch_text,
            "negative_prompt_guidance": "european medieval stone castles, gothic arches, classical greek marble columns, modern concrete",
            "strictness": "mandatory",
            "suggested_claim_statement": arch_statement,
            "confidence": 0.94,
        }
        res = self.detector.check_rule(arch_rule["rule_text"], arch_rule["category"], claims)
        arch_rule["conflict_warning"] = res.warning_text
        rules.append(arch_rule)

        # 5. Material Culture & Dress
        mat_rule = {
            "category": "material_culture",
            "title": "Handspun Khadi Drapes & Wrought Bronze/Iron",
            "rule_text": (
                "Garments are unstitched draped fabrics (antariya lower wraps, uttariya upper sashes) woven from handspun cotton. "
                "Armour features riveted bronze pectoral plates, hardened rawhide lamellae, and wrought iron spear points."
            ),
            "negative_prompt_guidance": "tailored medieval tunics with buttons, zippers, steel plate armor, velcro, synthetic fabrics",
            "strictness": "mandatory",
            "suggested_claim_statement": None,
            "confidence": 0.90,
        }
        res = self.detector.check_rule(mat_rule["rule_text"], mat_rule["category"], claims)
        mat_rule["conflict_warning"] = res.warning_text
        rules.append(mat_rule)

        # 6. Camera Language
        cam_rule = {
            "category": "camera_language",
            "title": "Observational Eye-Level & Deep Focus Spatial Staging",
            "rule_text": (
                "Camera maintains eye-level grounded human perspective. Wide shots utilize deep focus "
                "to preserve architectural context and geographic scale. Avoid exaggerated wide-angle distortion or impossible drone acrobatics."
            ),
            "negative_prompt_guidance": "fisheye distortion, acrobatic drone fpv, Dutch tilt excess, hyperactive camera shake",
            "strictness": "guideline",
            "suggested_claim_statement": None,
            "confidence": 0.91,
        }
        res = self.detector.check_rule(cam_rule["rule_text"], cam_rule["category"], claims)
        cam_rule["conflict_warning"] = res.warning_text
        rules.append(cam_rule)

        # If user gave specific notes that might introduce a conflict, parse and add a rule with detection
        if user_notes and len(user_notes.strip()) > 10:
            user_rule = {
                "category": "tone_aesthetic",
                "title": f"Director Visual Direction: {user_notes[:40]}...",
                "rule_text": user_notes.strip(),
                "negative_prompt_guidance": None,
                "strictness": "guideline",
                "suggested_claim_statement": None,
                "confidence": 0.85,
            }
            chk = self.detector.check_rule(user_rule["rule_text"], user_rule["category"], claims)
            if chk.has_conflict:
                user_rule["conflict_warning"] = chk.warning_text
                user_rule["strictness"] = "deliberate_deviation"
            else:
                user_rule["conflict_warning"] = None
            rules.append(user_rule)

        return rules

