"""Unit tests for packages/domain/journey.py's pure logic (GW1).

Complements tests/unit/test_journey_manifest.py, which validates the YAML's own
consistency against its sources; this file validates the ENGINE built on top of it:
applicability resolution and status derivation, with no database involved.
"""

from __future__ import annotations

from packages.domain.journey import (
    derive_group_status,
    derive_section_status,
    group_by_id,
    group_id_for_subpoint,
    group_passes_for_gating,
    is_released,
    resolve_applicability,
    section_by_id,
    section_id_for_group,
    sections,
)


def test_manifest_loads_the_full_10x70x140_structure():
    secs = sections()
    assert len(secs) == 10
    assert sum(len(s.groups) for s in secs) == 70
    assert sum(len(g.subpoints) for s in secs for g in s.groups) == 140
    assert [s.id for s in secs] == [f"JRN-{n:02d}" for n in range(1, 11)]


def test_group_and_section_lookup_round_trip():
    group = group_by_id("JRN-04.2")
    assert group.title == "Character identity profile"
    section = section_by_id("JRN-04")
    assert group in section.groups

    assert group_id_for_subpoint("JRN-04.2.1") == "JRN-04.2"
    assert section_id_for_group("JRN-04.2") == "JRN-04"


def test_capture_plan_applicability_matches_the_manifest_table():
    """JOURNEY_MANIFEST.md §5 table: JRN-07.4 is N/A in fully_ai unless a shot uses
    live_action_chroma or performance_transformation; it always applies in hybrid/mixed."""
    g = group_by_id("JRN-07.4")

    applies, reason = resolve_applicability(g, production_mode="fully_ai", shot_methods=frozenset())
    assert not applies
    assert "production mode" in reason

    applies, _ = resolve_applicability(
        g, production_mode="fully_ai", shot_methods=frozenset({"live_action_chroma"})
    )
    assert applies

    applies, _ = resolve_applicability(
        g, production_mode="fully_ai", shot_methods=frozenset({"digital_human"})
    )
    assert not applies, "digital_human is not one of the two exception methods (JM-10)"

    for mode in ("hybrid_live_action", "mixed"):
        applies, reason = resolve_applicability(g, production_mode=mode, shot_methods=frozenset())
        assert applies and reason is None


def test_groups_with_modes_all_always_apply():
    g = group_by_id("JRN-04.7")  # Consent and authorization: applies in every mode
    for mode in ("fully_ai", "hybrid_live_action", "mixed"):
        applies, reason = resolve_applicability(g, production_mode=mode, shot_methods=frozenset())
        assert applies and reason is None


def test_is_released_gates_only_pure_v2_groups():
    v1 = group_by_id("JRN-01.1")
    v1_v2 = group_by_id("JRN-07.4")
    v2 = group_by_id("JRN-08.4")  # Connected execution: release v2
    assert v2.release == "v2"

    assert is_released(v1, v2_enabled=False)
    assert is_released(v1_v2, v2_enabled=False)
    assert not is_released(v2, v2_enabled=False)
    assert is_released(v2, v2_enabled=True)


def test_group_status_completed_requires_every_subpoint_completed_or_na():
    assert derive_group_status(["completed", "completed"], applies=True, mode_na_reason=None) == "completed"
    assert derive_group_status(["completed", "not_applicable"], applies=True, mode_na_reason=None) == "completed"
    assert derive_group_status(["completed", "in_progress"], applies=True, mode_na_reason=None) == "in_progress"
    assert derive_group_status([], applies=True, mode_na_reason=None) == "not_started"
    assert derive_group_status(["not_started", "not_started"], applies=True, mode_na_reason=None) == "not_started"


def test_group_status_is_not_applicable_when_mode_excludes_it_regardless_of_subpoints():
    assert derive_group_status(["completed", "completed"], applies=False, mode_na_reason="x") == "not_applicable"
    assert derive_group_status([], applies=False, mode_na_reason="x") == "not_applicable"


def test_group_status_priority_stale_blocked_changes_review_in_progress():
    # Priority order matters: a single stale subpoint dominates everything else.
    assert derive_group_status(["completed", "stale"], applies=True, mode_na_reason=None) == "stale"
    assert derive_group_status(["stale", "blocked"], applies=True, mode_na_reason=None) == "stale"
    assert derive_group_status(["completed", "blocked"], applies=True, mode_na_reason=None) == "blocked"
    assert derive_group_status(["blocked", "changes_required"], applies=True, mode_na_reason=None) == "blocked"
    assert derive_group_status(["completed", "changes_required"], applies=True, mode_na_reason=None) == "changes_required"
    assert derive_group_status(["changes_required", "review_required"], applies=True, mode_na_reason=None) == "changes_required"
    assert derive_group_status(["completed", "review_required"], applies=True, mode_na_reason=None) == "review_required"


def test_group_passes_for_gating_only_completed_or_not_applicable():
    for status in ("completed", "not_applicable"):
        assert group_passes_for_gating(status)
    for status in ("not_started", "in_progress", "review_required", "changes_required", "blocked", "stale"):
        assert not group_passes_for_gating(status)


def test_section_ready_to_continue_only_when_every_group_passes():
    assert derive_section_status(["completed", "not_applicable", "completed"]) == "ready_to_continue"
    assert derive_section_status(["completed", "in_progress"]) == "in_progress"
    assert derive_section_status(["not_started", "not_started"]) == "not_started"
    assert derive_section_status(["completed", "blocked"]) == "blocked"
    assert derive_section_status([]) == "not_started"


def test_a_mode_excluded_group_does_not_make_an_untouched_section_look_started():
    """Regression: JRN-07.4 is not_applicable by mode in a fully-AI project with every
    other group of section 07 still not_started. The section must read not_started, not
    in_progress -- nothing has actually been worked on yet."""
    assert derive_section_status(["not_started", "not_started", "not_applicable", "not_started"]) == "not_started"
    # But a real not_applicable alongside genuine progress elsewhere is still in_progress.
    assert derive_section_status(["not_started", "in_progress", "not_applicable"]) == "in_progress"
