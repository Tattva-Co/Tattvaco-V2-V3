"""Deterministic cinematography recommendation generator (D6, TFD-CIN-004).

Parameterized on the director's own intent text via real keyword matching, the same
"real generator, not a hardcoded stub" quality bar as every other deterministic
generator in this codebase (ScreenplaySuggester, StoryboardAligner, etc.) -- every field
in a recommendation is driven by which keywords actually appear in the intent, with a
rationale string naming them.
"""

from __future__ import annotations

from typing import Any, Dict

#: Each entry: (keywords to match in the lowercased intent, value, rationale template).
#: The first matching entry wins; the last entry in each field's list is always the
#: keyword-free default.
_SHOT_TYPE_RULES = [
    (("wide", "vast", "establishing"), "wide shot", "intent mentions {kw} -> a wide shot establishes scale"),
    (("close", "intimate", "whisper"), "close-up", "intent mentions {kw} -> a close-up conveys intimacy"),
    ((), "medium shot", "no scale cue in the intent -> a medium shot is the neutral default"),
]
_POSITION_RULES = [
    (("epic", "powerful", "heroic", "warrior"), "low angle", "intent mentions {kw} -> a low angle reads as powerful/heroic"),
    (("vulnerable", "small", "afraid"), "high angle", "intent mentions {kw} -> a high angle reads as diminished/vulnerable"),
    ((), "eye level", "no power dynamic cued -> eye level is the neutral default"),
]
_LENS_RULES = [
    (("wide", "vast", "establishing"), "24mm wide-angle", "intent mentions {kw} -> a wide-angle lens matches the wide shot"),
    (("close", "intimate", "whisper"), "85mm portrait", "intent mentions {kw} -> a portrait lens compresses background for intimacy"),
    ((), "35mm standard", "no lens cue in the intent -> 35mm is the neutral default"),
]
_MOVEMENT_RULES = [
    (("first appearance", "entrance", "reveal"), "slow push-in", "intent mentions {kw} -> a slow push-in builds anticipation for a reveal"),
    (("chase", "action", "fight"), "handheld tracking", "intent mentions {kw} -> handheld tracking suits kinetic action"),
    ((), "static", "no motion cue in the intent -> a static shot is the neutral default"),
]
_LIGHTING_RULES = [
    (("sunset", "dusk", "golden"), "golden-hour backlight, warm rim light", "intent mentions {kw} -> golden-hour backlighting matches the time of day"),
    (("night", "dark", "shadow"), "low-key, practical sources only", "intent mentions {kw} -> low-key lighting matches a night setting"),
    ((), "soft natural key light", "no time-of-day cue in the intent -> soft natural light is the neutral default"),
]
_FRAMING_RULES = [
    (("epic", "powerful", "heroic"), "low-angle hero framing, rule of thirds", "intent mentions {kw} -> hero framing reinforces a powerful tone"),
    ((), "balanced rule-of-thirds framing", "no framing cue in the intent -> balanced rule-of-thirds is the neutral default"),
]
_BACKGROUND_RULES = [
    (("epic", "vast", "wide"), "expansive negative space behind the subject", "intent mentions {kw} -> negative space reinforces scale"),
    ((), "contextual environment, shallow background separation", "no scale cue in the intent -> a contextual background is the neutral default"),
]
_PLACEMENT_RULES = [
    (("first appearance", "entrance", "reveal"), "subject enters frame centre, establishing dominance", "intent mentions {kw} -> centre placement reads as a strong introduction"),
    ((), "subject off-centre per rule of thirds", "no entrance cue in the intent -> off-centre is the neutral default"),
]
_DURATION_RULES = [
    (("epic", "establishing", "first appearance"), "4-6 seconds (lingering establishing beat)", "intent mentions {kw} -> a longer hold lets an establishing beat land"),
    ((), "2-3 seconds", "no pacing cue in the intent -> a standard 2-3 second hold is the neutral default"),
]


def _match(rules, intent_lower: str) -> Dict[str, str]:
    for keywords, value, rationale_template in rules:
        hit = next((kw for kw in keywords if kw in intent_lower), None)
        if hit is not None:
            return {"value": value, "rationale": rationale_template.format(kw=f"'{hit}'")}
    _, default_value, default_rationale = rules[-1]
    return {"value": default_value, "rationale": default_rationale}


class CinematographyRecommender:
    """AT-CIN-004.1: given an intent string, recommends shot type, position, lens,
    movement, framing, lighting, background, placement, duration and references, each
    with a rationale -- no field is ever auto-applied by this generator; applying one is
    always a separate, explicit director action."""

    def recommend(self, intent: str) -> Dict[str, Dict[str, Any]]:
        intent_lower = intent.lower()
        fields = {
            "shot_type": _match(_SHOT_TYPE_RULES, intent_lower),
            "position": _match(_POSITION_RULES, intent_lower),
            "lens": _match(_LENS_RULES, intent_lower),
            "movement": _match(_MOVEMENT_RULES, intent_lower),
            "framing": _match(_FRAMING_RULES, intent_lower),
            "lighting": _match(_LIGHTING_RULES, intent_lower),
            "background": _match(_BACKGROUND_RULES, intent_lower),
            "placement": _match(_PLACEMENT_RULES, intent_lower),
            "duration": _match(_DURATION_RULES, intent_lower),
        }
        references = [f"{field}: {data['value']}" for field, data in fields.items()]
        fields["references"] = {
            "value": references,
            "rationale": "one reference note per recommended field, for quick director scanning",
        }
        for data in fields.values():
            data["metadata_origin"] = "recommended"
        return fields
