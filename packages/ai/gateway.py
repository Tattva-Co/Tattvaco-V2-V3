"""ModelGateway (C10): the one seam between a workflow graph's node function and
whatever actually generates candidate content.

Today the only implementation is `DeterministicModelGateway`, a thin, Pydantic-validating
wrapper around the 4 generators that already existed (packages/workflows/{script_
intelligence/parser,historical_research/investigator,storyboard_intelligence/aligner,
film_bible_synthesis/synthesizer}.py) -- their own logic is untouched (deliberately: they
have real behaviour worth preserving, parameterised on real input, not just placeholder
noise), only now called through a formal interface with a validated, typed output shape
instead of a bare dict. A future real-LLM adapter implements the exact same `ModelGateway`
ABC, behind the exact same Pydantic models (packages/ai/schemas.py) -- every caller
(the 4 graphs) is already written against the interface, not the deterministic adapter,
so swapping one in is a `get_model_gateway` config change, not a graph rewrite.

`mode` labels every run this gateway starts and every candidate it proposes
(WorkflowRunModel.generator_mode, *CandidateModel.generator_mode) -- "the mode is visible
in the UI" (C10 exit criterion) means a reviewer looking at a candidate can always tell
whether a human or a machine should be trusted to have actually produced it, and which
kind of machine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import ValidationError

from packages.ai.schemas import (
    FilmBibleSynthesisResult,
    HistoricalResearchResult,
    ScreenplayParseResult,
    ScreenplaySuggestionResult,
    StoryboardAlignResult,
)
from packages.core.config import Settings
from packages.domain.errors import ValidationFailure

GENERATOR_MODE_DETERMINISTIC = "deterministic"
GENERATOR_MODE_LLM = "llm"


def _validated(model_cls, **kwargs):
    """Wrap a generator's raw dict output in its Pydantic model, turning a malformed
    shape into one clear ValidationFailure (422) instead of a KeyError or TypeError deep
    inside a later DB-write transaction."""
    try:
        return model_cls(**kwargs)
    except ValidationError as exc:
        raise ValidationFailure(f"{model_cls.__name__} produced an invalid shape: {exc}") from exc


class ModelGateway(ABC):
    @property
    @abstractmethod
    def mode(self) -> str:
        """GENERATOR_MODE_* -- persisted on the run and every candidate it proposes."""

    @abstractmethod
    def parse_screenplay(self, text: str) -> ScreenplayParseResult: ...

    @abstractmethod
    def investigate_history(self, topic: str, seed_text: str | None) -> HistoricalResearchResult: ...

    @abstractmethod
    def align_storyboard(self, scenes: list[dict], brief: str | None) -> StoryboardAlignResult: ...

    @abstractmethod
    def synthesize_film_bible(
        self, scenes: list[dict], claims: list[dict], user_notes: str | None
    ) -> FilmBibleSynthesisResult: ...

    @abstractmethod
    def suggest_screenplay_revisions(
        self, content_text: str, scope_notes: str | None
    ) -> ScreenplaySuggestionResult: ...


class DeterministicModelGateway(ModelGateway):
    """Wraps the pre-existing generators. See module docstring."""

    mode = GENERATOR_MODE_DETERMINISTIC

    def __init__(self) -> None:
        # Deferred: these generator modules live under packages.workflows, whose own
        # __init__ re-exports pull in this gateway module -- importing them at gateway
        # module load time creates a circular import. By construction time (a node
        # function actually running), every module involved is already fully loaded.
        from packages.workflows.film_bible_synthesis.synthesizer import FilmBibleSynthesizer
        from packages.workflows.historical_research.investigator import HistoricalInvestigator
        from packages.workflows.screenplay_suggestions.suggester import ScreenplaySuggester
        from packages.workflows.script_intelligence.parser import ScreenplayParser
        from packages.workflows.storyboard_intelligence.aligner import StoryboardAligner

        self._parser = ScreenplayParser()
        self._investigator = HistoricalInvestigator()
        self._aligner = StoryboardAligner()
        self._synthesizer = FilmBibleSynthesizer()
        self._suggester = ScreenplaySuggester()

    def parse_screenplay(self, text: str) -> ScreenplayParseResult:
        scenes, entities, dialogue_segments = self._parser.parse(text)
        return _validated(
            ScreenplayParseResult, scenes=scenes, entities=entities, dialogue_segments=dialogue_segments
        )

    def investigate_history(self, topic: str, seed_text: str | None) -> HistoricalResearchResult:
        claims, questions = self._investigator.investigate(topic, seed_text)
        return _validated(HistoricalResearchResult, claims=claims, questions=questions)

    def align_storyboard(self, scenes: list[dict], brief: str | None) -> StoryboardAlignResult:
        panels = self._aligner.generate_panels(scenes, brief=brief)
        return _validated(StoryboardAlignResult, panels=panels)

    def synthesize_film_bible(
        self, scenes: list[dict], claims: list[dict], user_notes: str | None
    ) -> FilmBibleSynthesisResult:
        rules = self._synthesizer.synthesize_rules(scenes, claims, user_notes=user_notes)
        return _validated(FilmBibleSynthesisResult, rules=rules)

    def suggest_screenplay_revisions(
        self, content_text: str, scope_notes: str | None
    ) -> ScreenplaySuggestionResult:
        suggestions = self._suggester.suggest(content_text, scope_notes=scope_notes)
        return _validated(ScreenplaySuggestionResult, suggestions=suggestions)


def get_model_gateway(settings: Settings) -> ModelGateway:
    if settings.model_gateway_provider == "deterministic":
        return DeterministicModelGateway()
    raise ValueError(f"Unsupported model gateway provider: {settings.model_gateway_provider}")
