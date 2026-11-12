"""Production format template catalogue (D1, TFD-FMT-001/004; PRD §8).

Configuration data, not a database table: the 13 formats, their structure and workflow
steps are fixed product shape (PRD §8's own list), while the per-format numeric defaults
inside ``default_output_profile`` are explicitly open pending production validation
(DEC-028 -- "template default values, not the mechanism"). ``GET /project-templates``
(TFD-FMT-001) serves this list read-only; a project stores only the chosen ``key`` on
``ProjectModel.format_template_key``.

``required_workflow_steps``/``optional_workflow_steps`` name Guided Workspace journey
sections (``packages/domain/journey_manifest.yaml``, JRN-02..JRN-10 -- JRN-01 Project
Workspace & Setup is the universal gate every format needs and is not listed here).
"Formats do not share one workflow" (TFD-FMT-004): a format's optional steps are
configured, never forced -- e.g. Reel marks JRN-07 (Production Planning/sequencing)
optional (AT-FMT-001.2: "sequence planning is marked optional, and packaging does not
require sequences").
"""

from __future__ import annotations

from dataclasses import dataclass, field

ALL_WORKFLOW_STEPS: tuple[str, ...] = (
    "JRN-02",  # Screenplay & Governance
    "JRN-03",  # Research & Story Intelligence
    "JRN-04",  # Character & Digital Human Studio
    "JRN-05",  # Visual World Development
    "JRN-06",  # Cinematography & Storyboard Studio
    "JRN-07",  # Production Planning
    "JRN-08",  # AI Production & Tool Handoff
    "JRN-09",  # Output Inspection & Continuity Approval
    "JRN-10",  # Production Library & Delivery
)


@dataclass(frozen=True)
class FormatTemplate:
    key: str
    name: str
    structure_type: str  # "linear" | "episodic"
    optional_workflow_steps: tuple[str, ...] = ()
    default_output_profile: dict = field(default_factory=dict)
    note: str | None = None

    @property
    def required_workflow_steps(self) -> tuple[str, ...]:
        return tuple(s for s in ALL_WORKFLOW_STEPS if s not in self.optional_workflow_steps)


def _profile(
    *, resolution: str, aspect_ratio: str, fps: int, duration_target_seconds: int, delivery_format: str
) -> dict:
    return {
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "fps": fps,
        "duration_target_seconds": duration_target_seconds,
        "delivery_format": delivery_format,
    }


FORMAT_TEMPLATES: tuple[FormatTemplate, ...] = (
    FormatTemplate(
        key="feature_film",
        name="Feature Film",
        structure_type="linear",
        default_output_profile=_profile(
            resolution="3840x2160", aspect_ratio="2.39:1", fps=24, duration_target_seconds=5400,
            delivery_format="ProRes 4444",
        ),
    ),
    FormatTemplate(
        key="ott_series",
        name="OTT Series",
        structure_type="episodic",
        default_output_profile=_profile(
            resolution="3840x2160", aspect_ratio="16:9", fps=24, duration_target_seconds=2700,
            delivery_format="ProRes 4444",
        ),
    ),
    FormatTemplate(
        key="episodic_historical_series",
        name="Episodic Historical Series",
        structure_type="episodic",
        default_output_profile=_profile(
            resolution="3840x2160", aspect_ratio="16:9", fps=24, duration_target_seconds=2700,
            delivery_format="ProRes 4444",
        ),
    ),
    FormatTemplate(
        key="short_film",
        name="Short Film",
        structure_type="linear",
        default_output_profile=_profile(
            resolution="1920x1080", aspect_ratio="16:9", fps=24, duration_target_seconds=900,
            delivery_format="H.264 MP4",
        ),
    ),
    FormatTemplate(
        key="trailer",
        name="Trailer",
        structure_type="linear",
        optional_workflow_steps=("JRN-02", "JRN-03", "JRN-04", "JRN-05", "JRN-06", "JRN-07"),
        default_output_profile=_profile(
            resolution="1920x1080", aspect_ratio="2.39:1", fps=24, duration_target_seconds=120,
            delivery_format="H.264 MP4",
        ),
        note="References shots from a parent project (PRD §8); its own mid-pipeline "
        "sections are optional rather than required.",
    ),
    FormatTemplate(
        key="teaser",
        name="Teaser",
        structure_type="linear",
        optional_workflow_steps=("JRN-02", "JRN-03", "JRN-04", "JRN-05", "JRN-06", "JRN-07"),
        default_output_profile=_profile(
            resolution="1920x1080", aspect_ratio="2.39:1", fps=24, duration_target_seconds=45,
            delivery_format="H.264 MP4",
        ),
        note="References shots from a parent project (PRD §8); its own mid-pipeline "
        "sections are optional rather than required.",
    ),
    FormatTemplate(
        key="documentary",
        name="Documentary",
        structure_type="linear",
        optional_workflow_steps=("JRN-02",),
        default_output_profile=_profile(
            resolution="1920x1080", aspect_ratio="16:9", fps=24, duration_target_seconds=3600,
            delivery_format="ProRes 422",
        ),
        note="Footage-first: screenplay lock is optional, a story-outline artifact "
        "governs instead (PRD §8).",
    ),
    FormatTemplate(
        key="vertical_film",
        name="Vertical Film",
        structure_type="linear",
        default_output_profile=_profile(
            resolution="1080x1920", aspect_ratio="9:16", fps=30, duration_target_seconds=300,
            delivery_format="H.264 MP4",
        ),
    ),
    FormatTemplate(
        key="social_media_video",
        name="Social Media Video",
        structure_type="linear",
        optional_workflow_steps=("JRN-07",),
        default_output_profile=_profile(
            resolution="1080x1080", aspect_ratio="1:1", fps=30, duration_target_seconds=60,
            delivery_format="H.264 MP4",
        ),
    ),
    FormatTemplate(
        key="reel",
        name="Reel",
        structure_type="linear",
        optional_workflow_steps=("JRN-07",),
        default_output_profile=_profile(
            resolution="1080x1920", aspect_ratio="9:16", fps=30, duration_target_seconds=30,
            delivery_format="H.264 MP4",
        ),
        note="AT-FMT-001.2: sequence planning (JRN-07) is optional; packaging does not "
        "require sequences.",
    ),
    FormatTemplate(
        key="branded_content",
        name="Branded Content",
        structure_type="linear",
        default_output_profile=_profile(
            resolution="1920x1080", aspect_ratio="16:9", fps=24, duration_target_seconds=60,
            delivery_format="H.264 MP4",
        ),
    ),
    FormatTemplate(
        key="promotional_content",
        name="Promotional Content",
        structure_type="linear",
        default_output_profile=_profile(
            resolution="1920x1080", aspect_ratio="16:9", fps=24, duration_target_seconds=90,
            delivery_format="H.264 MP4",
        ),
    ),
    FormatTemplate(
        key="educational_content",
        name="Educational Content",
        structure_type="linear",
        default_output_profile=_profile(
            resolution="1920x1080", aspect_ratio="16:9", fps=24, duration_target_seconds=600,
            delivery_format="H.264 MP4",
        ),
    ),
)

FORMAT_TEMPLATES_BY_KEY: dict[str, FormatTemplate] = {t.key: t for t in FORMAT_TEMPLATES}

assert len(FORMAT_TEMPLATES) == 13, "PRD §8 lists exactly 13 production formats (AT-FMT-001.1)"
