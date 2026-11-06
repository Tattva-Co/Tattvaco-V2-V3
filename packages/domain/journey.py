"""The Guided Workspace journey engine's pure domain logic (GW1).

Reads packages/domain/journey_manifest.yaml (the manifest; see docs/product/
JOURNEY_MANIFEST.md) and implements the parts of the section completion algorithm that
don't need a database: applicability resolution, and deriving a group's or section's
status from its children's statuses. Everything here is a pure function over plain data,
so it is tested without a database. The parts that DO need the database -- reading and
writing journey_item_states, evaluating `system` completion checks against domain
tables, and persisting section-continue events -- live in packages/services/journey.py.

Terminology (JOURNEY_MANIFEST.md §1): a project's journey has 10 Sections, each with
several Groups (accordions), each with 2+ Subpoints (the actionable steps; status is
tracked per subpoint). IDs are permanent: `JRN-<section>` / `JRN-<section>.<group>` /
`JRN-<section>.<group>.<subpoint>`.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_MANIFEST_PATH = Path(__file__).with_name("journey_manifest.yaml")

# Status vocabularies (JOURNEY_MANIFEST.md §6). Kept as plain strings, not an Enum: they
# are persisted as-is and validated against these sets at the boundary (service layer),
# matching every other status column in this codebase (packages/domain/enums.py).
ITEM_STATUSES = frozenset(
    {
        "not_started",
        "in_progress",
        "review_required",
        "changes_required",
        "blocked",
        "completed",
        "not_applicable",
        "stale",
    }
)
SECTION_STATUSES = frozenset({"not_started", "in_progress", "blocked", "ready_to_continue", "completed"})

# A group is "incomplete" for section-gating purposes in every status except these two
# (JOURNEY_MANIFEST.md §6, step 6-7).
_GROUP_PASSING_STATUSES = frozenset({"completed", "not_applicable"})


@lru_cache
def load_manifest() -> dict[str, Any]:
    """The parsed manifest. Cached: it is static application data, not configuration
    that changes per request or per environment."""
    return yaml.safe_load(_MANIFEST_PATH.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Subpoint:
    id: str  # JRN-<section>.<group>.<n>
    group_id: str
    key: str
    title: str
    kind: str  # "work" | "review_gate"
    description: str


@dataclass(frozen=True)
class Group:
    id: str  # JRN-<section>.<group>
    section_id: str
    title: str
    purpose: str
    completion_rule: str
    required: bool
    na_policy: str  # "never" | "reason_required"
    release: str  # "v1" | "v1_v2" | "v2"
    applicability: dict[str, Any]
    act_capability: str
    approval_capability: str | None
    completion_check: dict[str, Any]  # {"kind": "manual_with_evidence"} or {"kind": "system", "key": "..."}
    studio_tools: tuple[str, ...]
    requirements: tuple[str, ...]
    subpoints: tuple[Subpoint, ...]


@dataclass(frozen=True)
class Section:
    id: str  # JRN-<nn>
    title: str
    release_label: str
    groups: tuple[Group, ...]


def _build_subpoints(group_raw: dict[str, Any], manifest: dict[str, Any]) -> tuple[Subpoint, ...]:
    explicit = group_raw.get("subpoints")
    template = explicit if explicit is not None else manifest["subpoint_template"]
    return tuple(
        Subpoint(
            id=f"{group_raw['id']}.{item['suffix']}",
            group_id=group_raw["id"],
            key=item["key"],
            title=item["title"],
            kind=item["kind"],
            description=item["description"],
        )
        for item in template
    )


@lru_cache
def sections() -> tuple[Section, ...]:
    """Every section, in manifest order, with groups and subpoints fully materialized."""
    manifest = load_manifest()
    result = []
    for section_raw in manifest["sections"]:
        groups = tuple(
            Group(
                id=g["id"],
                section_id=section_raw["id"],
                title=g["title"],
                purpose=g["purpose"],
                completion_rule=g["completion_rule"],
                required=g["required"],
                na_policy=g["na"],
                release=g["release"],
                applicability=g["applicability"],
                act_capability=g["act_capability"],
                approval_capability=g.get("approval_capability"),
                completion_check=g["completion_check"],
                studio_tools=tuple(g["studio_tools"]),
                requirements=tuple(g["requirements"]),
                subpoints=_build_subpoints(g, manifest),
            )
            for g in section_raw["groups"]
            if not g.get("retired", False)
        )
        result.append(
            Section(id=section_raw["id"], title=section_raw["title"], release_label=section_raw["release_label"], groups=groups)
        )
    return tuple(result)


def group_by_id(jrn_group_id: str) -> Group:
    for section in sections():
        for group in section.groups:
            if group.id == jrn_group_id:
                return group
    raise KeyError(f"Unknown journey group id: {jrn_group_id!r}")


def section_by_id(jrn_section_id: str) -> Section:
    for section in sections():
        if section.id == jrn_section_id:
            return section
    raise KeyError(f"Unknown journey section id: {jrn_section_id!r}")


def group_id_for_subpoint(jrn_subpoint_id: str) -> str:
    """'JRN-02.1.1' -> 'JRN-02.1'."""
    return jrn_subpoint_id.rsplit(".", 1)[0]


def section_id_for_group(jrn_group_id: str) -> str:
    """'JRN-02.1' -> 'JRN-02'."""
    return jrn_group_id.split(".", 1)[0]


# -- Applicability (JOURNEY_MANIFEST.md §5) ----------------------------------------


def is_released(group: Group, *, v2_enabled: bool) -> bool:
    """A group whose release isn't shipped yet is absent entirely (not shown as a
    teaser), per IA §4.2 rule 4. v1_v2 groups ship in both; only pure v2 groups are
    gated on v2_enabled."""
    if group.release == "v2":
        return v2_enabled
    return True


def resolve_applicability(group: Group, *, production_mode: str, shot_methods: frozenset[str]) -> tuple[bool, str | None]:
    """(applies, reason_if_not). A group inapplicable by mode is still shown (status
    not_applicable with this reason), never hidden (JOURNEY_MANIFEST.md §5, step 4)."""
    modes = group.applicability.get("modes", "all")
    if modes == "all" or production_mode in modes:
        return True, None
    for condition in group.applicability.get("unless_any", []):
        for name, values in condition.items():
            if name == "shot_method_in" and shot_methods & set(values):
                return True, None
            # Any other condition name is a manifest bug caught by
            # tests/unit/test_journey_manifest.py, not something to fail open on here.
    return False, "Not applicable for the selected production mode"


# -- Status derivation (JOURNEY_MANIFEST.md §6) ------------------------------------


def derive_group_status(subpoint_statuses: list[str], *, applies: bool, mode_na_reason: str | None) -> str:
    """A group is `completed` when every subpoint is `completed`, or when the group is
    `not_applicable` (either by mode, or by an explicit user mark carried in the
    subpoint statuses -- both end up as `not_applicable` subpoint statuses)."""
    if not applies:
        return "not_applicable"
    if not subpoint_statuses:
        return "not_started"
    if all(s in ("completed", "not_applicable") for s in subpoint_statuses):
        return "completed"
    if any(s == "stale" for s in subpoint_statuses):
        return "stale"
    if any(s == "blocked" for s in subpoint_statuses):
        return "blocked"
    if any(s == "changes_required" for s in subpoint_statuses):
        return "changes_required"
    if any(s == "review_required" for s in subpoint_statuses):
        return "review_required"
    if any(s in ("in_progress", "completed", "not_applicable") for s in subpoint_statuses):
        return "in_progress"
    return "not_started"


def group_passes_for_gating(group_status: str) -> bool:
    """Whether this group's current status lets the section advance (§6 step 6-7)."""
    return group_status in _GROUP_PASSING_STATUSES


def derive_section_status(group_statuses: list[str]) -> str:
    if not group_statuses:
        return "not_started"
    if all(group_passes_for_gating(s) for s in group_statuses):
        return "ready_to_continue"
    if any(s == "blocked" for s in group_statuses):
        return "blocked"
    # A group that is not_applicable purely because of the project's mode represents no
    # work at all, not work "done" or "in progress" -- it must not make an otherwise
    # untouched section look started (e.g. a fully-AI project's section 07, where the
    # only non-not_started group is the mode-excluded capture plan).
    if all(s in ("not_started", "not_applicable") for s in group_statuses):
        return "not_started"
    return "in_progress"
