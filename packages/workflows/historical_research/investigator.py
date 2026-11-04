"""Deterministic Historical Research engine / mock LLM adapter for offline validation.

Extracts structured claims, source tiers, confidence ratings, and open questions
based on the research brief and project context.
"""

from __future__ import annotations

from typing import Any


class HistoricalInvestigator:
    """Extracts research claims, source provenance, and open questions from research briefs."""

    def investigate(self, topic: str, seed_text: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        topic_lower = topic.lower()

        claims: list[dict[str, Any]] = []
        questions: list[dict[str, Any]] = []

        if "kalinga" in topic_lower or "maurya" in topic_lower or "ashoka" in topic_lower:
            claims.extend([
                {
                    "statement": "Unstitched fine cotton antariya (lower drape) and uttariya (upper scarf) constituted the primary aristocratic attire, with no evidence of tailored seam stitches.",
                    "claim_class": "historical_fact",
                    "era_or_date": "c. 261 BCE (Mauryan era)",
                    "location": "Kalinga / Tosali",
                    "confidence": 0.95,
                    "source_title": "Archaeological Survey of India: Dhauli & Jaugada Inscriptions",
                    "source_tier": "tier_1_primary",
                    "source_locator": "Major Rock Edict XIII, Corpus Inscriptionum Indicarum Vol. I",
                },
                {
                    "statement": "Fortification walls at Sisupalgarh utilized baked brick and stone ramparts with defensive perimeter moats.",
                    "claim_class": "historical_fact",
                    "era_or_date": "3rd Century BCE",
                    "location": "Sisupalgarh / Kalinga",
                    "confidence": 0.92,
                    "source_title": "Excavations at Sisupalgarh: Early Historic Urban Architecture",
                    "source_tier": "tier_2_scholarly",
                    "source_locator": "Ancient India Journal, No. 5, pp. 62-105",
                },
                {
                    "statement": "Warfare involved standard-issue double-edged broadswords and bamboo longbows with cane arrows tipped with forged iron.",
                    "claim_class": "historical_interpretation",
                    "era_or_date": "c. 261 BCE",
                    "location": "Eastern India",
                    "confidence": 0.88,
                    "source_title": "Military History of Ancient India",
                    "source_tier": "tier_2_scholarly",
                    "source_locator": "Ch. 4 (Mauryan Military Formations)",
                },
            ])
            questions.extend([
                {
                    "text": "What specific vegetable dyes were accessible for military officer insignia versus common infantry attire in coastal Kalinga?",
                    "category": "costume",
                },
                {
                    "text": "Did the Kalinga naval militia maintain distinctive vessel designs differing from coastal merchant dhows?",
                    "category": "naval_architecture",
                },
            ])
        elif "chola" in topic_lower or "rajaraja" in topic_lower or "thanjavur" in topic_lower:
            claims.extend([
                {
                    "statement": "Brihadisvara Temple granite architecture was constructed without mortar using interlocking precision stone joints.",
                    "claim_class": "historical_fact",
                    "era_or_date": "c. 1010 CE",
                    "location": "Thanjavur",
                    "confidence": 0.98,
                    "source_title": "The Cholas — K.A. Nilakanta Sastri",
                    "source_tier": "tier_2_scholarly",
                    "source_locator": "Vol. II, Part 1, pp. 240-258",
                },
                {
                    "statement": "Naval expeditions to Sri Vijaya deployed multi-tiered oared warships equipped with fire catapults and boarding archers.",
                    "claim_class": "historical_interpretation",
                    "era_or_date": "c. 1025 CE",
                    "location": "Bay of Bengal / Straits of Malacca",
                    "confidence": 0.85,
                    "source_title": "South Indian Inscriptions: Rajendra Chola Maritime Epigraphy",
                    "source_tier": "tier_1_primary",
                    "source_locator": "Epigraphia Indica, Vol. IX",
                },
            ])
            questions.extend([
                {
                    "text": "What ceremonial headwear (makuta/karanda) distinguished royal naval commanders during coronation ceremonies?",
                    "category": "costume",
                },
            ])
        else:
            # General historical inquiry
            claims.extend([
                {
                    "statement": f"Historical baseline establishing geographical and material culture parameters for '{topic}'.",
                    "claim_class": "historical_fact",
                    "era_or_date": "Historical Period",
                    "location": topic,
                    "confidence": 0.90,
                    "source_title": f"Historical Archive Record for {topic}",
                    "source_tier": "tier_2_scholarly",
                    "source_locator": "General Survey, Document 1",
                },
                {
                    "statement": f"Cultural and architectural visual rules inferred from contemporaneous regional evidence for '{topic}'.",
                    "claim_class": "historical_interpretation",
                    "era_or_date": "Historical Period",
                    "location": topic,
                    "confidence": 0.85,
                    "source_title": f"Cultural Monograph on {topic}",
                    "source_tier": "tier_2_scholarly",
                    "source_locator": "Section 2.3",
                },
            ])
            questions.extend([
                {
                    "text": f"What primary archaeological evidence verifies the exact material composition of residential structures in {topic}?",
                    "category": "architecture",
                },
                {
                    "text": f"Are there contested accounts of ritual practices during this era in {topic}?",
                    "category": "cultural_practice",
                },
            ])

        if seed_text:
            claims.append({
                "statement": f"User brief assertion: {seed_text[:200]}",
                "claim_class": "user_assertion",
                "era_or_date": "Specified in brief",
                "location": "Project Brief",
                "confidence": 0.80,
                "source_title": "Director Project Dossier Brief",
                "source_tier": "tier_0_project",
                "source_locator": "Brief Section 1",
            })

        return claims, questions

