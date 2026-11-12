"""Structured-output contracts for every generation capability (C10).

Each model's required/optional fields and defaults mirror exactly what the
corresponding review service already expects (packages/services/{script_review,
research_review,storyboard_review,film_bible_review}.py) -- before this, a malformed
dict reaching `propose()` failed with a bare `KeyError` deep inside a DB-write
transaction; now it fails here, before any workflow node or service method runs, with a
clear `pydantic.ValidationError` (packages/ai/gateway.py wraps that into a domain
`ValidationFailure`). This is exactly the protection a future real-LLM adapter needs:
nothing about an LLM's output is trustworthy until it has passed through here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SceneCandidateData(BaseModel):
    scene_number: int
    heading: str
    setting: str
    location_name: str
    time_of_day: str
    summary: str
    source_locator: str
    characters_present: list[str] = Field(default_factory=list)


class EntityCandidateData(BaseModel):
    name: str
    category: str
    description: str | None = None
    source_locator: str
    confidence: float = 0.9


class ScreenplayParseResult(BaseModel):
    scenes: list[SceneCandidateData] = Field(default_factory=list)
    entities: list[EntityCandidateData] = Field(default_factory=list)


class ResearchClaimData(BaseModel):
    statement: str
    claim_class: str = "historical_fact"
    era_or_date: str | None = None
    location: str | None = None
    confidence: float = 0.9
    source_title: str = "General Historical Record"
    source_tier: str = "tier_2_scholarly"
    source_locator: str | None = None


class ResearchQuestionData(BaseModel):
    text: str
    category: str = "general"


class HistoricalResearchResult(BaseModel):
    claims: list[ResearchClaimData] = Field(default_factory=list)
    questions: list[ResearchQuestionData] = Field(default_factory=list)


class StoryboardPanelData(BaseModel):
    panel_number: int
    description: str
    suggested_scene_number: int | None = None
    shot_type: str = "wide"
    visual_notes: str | None = None
    dialogue_snippet: str | None = None
    confidence: float = 0.9


class StoryboardAlignResult(BaseModel):
    panels: list[StoryboardPanelData] = Field(default_factory=list)


class FilmBibleRuleData(BaseModel):
    category: str
    title: str
    rule_text: str
    negative_prompt_guidance: str | None = None
    strictness: str = "guideline"
    suggested_claim_statement: str | None = None
    confidence: float = 0.9
    conflict_warning: str | None = None


class FilmBibleSynthesisResult(BaseModel):
    rules: list[FilmBibleRuleData] = Field(default_factory=list)


class ScreenplaySuggestionData(BaseModel):
    kind: str
    anchor: str
    suggestion_text: str
    rationale: str | None = None
    confidence: float = 0.75


class ScreenplaySuggestionResult(BaseModel):
    suggestions: list[ScreenplaySuggestionData] = Field(default_factory=list)
