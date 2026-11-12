"""API-level integration tests for the Guided Workspace journey engine (GW1).

tests/unit/test_journey_domain.py covers the pure applicability/status logic;
tests/unit/test_journey_manifest.py validates the manifest itself. This file exercises
the full stack: API -> JourneyService -> JourneyRepository -> Postgres, including the
system-derived completion checks against real G-01..G-04 domain data, RBAC gating, and
the section-continue gate.
"""

from __future__ import annotations

from tests.support import as_actor, create_project, upload_script


def _journey(client, tenant, project_id: str) -> list[dict]:
    return client.get(f"/api/v1/projects/{project_id}/journey", headers=as_actor(tenant.user_id)).json()


def _section(journey: list[dict], section_id: str) -> dict:
    return next(s for s in journey if s["id"] == section_id)


def _group(journey: list[dict], group_id: str) -> dict:
    for section in journey:
        for group in section["groups"]:
            if group["id"] == group_id:
                return group
    raise KeyError(group_id)


def test_a_fresh_project_has_all_ten_sections_not_started(client, tenant):
    project = create_project(client, tenant)
    journey = _journey(client, tenant, project["id"])

    assert [s["id"] for s in journey] == [f"JRN-{n:02d}" for n in range(1, 11)]
    for section in journey:
        assert section["status"] == "not_started"
        assert section["can_continue"] is False
        for group in section["groups"]:
            if not group["applies"]:
                # JRN-07.4 (On-set capture plan) is the only group with non-"all"
                # applicability (hybrid_live_action/mixed only); it does not appear
                # here for this project's default "mixed" mode (D1, AT-PRJ-001.3), but
                # the branch is kept for whichever project configuration does exclude
                # a group -- correct, not "untouched".
                assert group["status"] == "not_applicable"
                continue
            assert group["status"] == "not_started"
            for subpoint in group["subpoints"]:
                assert subpoint["status"] == "not_started"


def test_pure_v2_groups_are_absent_not_shown_as_teasers(client, tenant):
    project = create_project(client, tenant)
    journey = _journey(client, tenant, project["id"])
    group_ids = {g["id"] for s in journey for g in s["groups"]}
    assert "JRN-08.4" not in group_ids, "Connected execution is release=v2; V2 is not enabled yet"
    assert "JRN-07.4" in group_ids, "v1_v2 groups still appear"


def test_draft_and_complete_a_manual_subpoint(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    jrn = "JRN-05.3.1"  # Architecture and materials / prepare -- plain manual check

    draft = client.post(f"/api/v1/projects/{project['id']}/journey/items/{jrn}", json={"action": "draft"}, headers=headers)
    assert draft.status_code == 200, draft.text
    assert draft.json()["status"] == "in_progress"

    complete = client.post(
        f"/api/v1/projects/{project['id']}/journey/items/{jrn}", json={"action": "complete"}, headers=headers
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "completed"

    group = _group(_journey(client, tenant, project["id"]), "JRN-05.3")
    assert group["subpoints"][0]["status"] == "completed"


def test_not_applicable_requires_a_reason_when_policy_demands_it(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    jrn = "JRN-05.5.1"  # Props and weapons: na reason_required

    no_reason = client.post(
        f"/api/v1/projects/{project['id']}/journey/items/{jrn}", json={"action": "not_applicable"}, headers=headers
    )
    assert no_reason.status_code == 422, no_reason.text

    with_reason = client.post(
        f"/api/v1/projects/{project['id']}/journey/items/{jrn}",
        json={"action": "not_applicable", "not_applicable_reason": "No weapons in this story"},
        headers=headers,
    )
    assert with_reason.status_code == 200, with_reason.text
    assert with_reason.json()["status"] == "not_applicable"


def test_na_never_group_cannot_be_marked_not_applicable(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    resp = client.post(
        f"/api/v1/projects/{project['id']}/journey/items/JRN-01.1.1",
        json={"action": "not_applicable", "not_applicable_reason": "whatever"},
        headers=headers,
    )
    assert resp.status_code == 409, resp.text


def test_system_check_completes_automatically_from_real_script_intelligence_data(client, tenant):
    """JRN-02.1 (Import screenplay): the validate subpoint is system-checked on
    screenplay_asset_present. It must become completed once a script asset exists, with
    no direct user action on that subpoint -- and a direct 'complete' call must be
    rejected, since the server derives this one, not the user."""
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)

    before = _group(_journey(client, tenant, project["id"]), "JRN-02.1")
    assert before["subpoints"][1]["status"] == "not_started"
    assert before["system_managed"] is True, (
        "the web client (apps/web/src/components/SubpointRow.tsx) hides the manual "
        "'Mark complete' action for the validate subpoint using this flag"
    )

    forced = client.post(
        f"/api/v1/projects/{project['id']}/journey/items/JRN-02.1.2", json={"action": "complete"}, headers=headers
    )
    assert forced.status_code == 409, forced.text

    upload_script(client, tenant, project["id"])

    after = _group(_journey(client, tenant, project["id"]), "JRN-02.1")
    assert after["subpoints"][1]["status"] == "completed"
    assert after["status"] in ("in_progress", "completed")


def test_system_managed_is_false_for_manually_validated_groups(client, tenant):
    project = create_project(client, tenant)
    group = _group(_journey(client, tenant, project["id"]), "JRN-05.3")
    assert group["system_managed"] is False


def test_capture_plan_group_is_not_applicable_for_fully_ai_projects(client, tenant):
    # D1 (AT-PRJ-001.3): project creation without an explicit mode now defaults to
    # "mixed", under which JRN-07.4 DOES apply (journey_manifest.yaml:
    # modes: [hybrid_live_action, mixed]) -- this test is specifically about fully_ai,
    # so it must ask for that mode explicitly rather than rely on the default.
    project = create_project(client, tenant, production_mode="fully_ai")
    group = _group(_journey(client, tenant, project["id"]), "JRN-07.4")
    assert group["status"] == "not_applicable"
    assert group["applies"] is False
    assert "production mode" in group["applicability_reason"]


def test_section_cannot_continue_while_required_groups_are_incomplete(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)
    resp = client.post(f"/api/v1/projects/{project['id']}/journey/sections/JRN-01/continue", headers=headers)
    assert resp.status_code == 409, resp.text


def test_section_continue_succeeds_once_every_group_passes_and_is_recorded(client, tenant):
    project = create_project(client, tenant)
    headers = as_actor(tenant.user_id)

    # Section 01 has 7 groups, all na: reason_required or never, all act_capability
    # project.admin -- satisfy every one by marking it not_applicable where allowed and
    # completing where na:never (01.1-01.4 are never, so complete both subpoints there).
    import packages.domain.journey as journey_mod

    section_01 = journey_mod.section_by_id("JRN-01")
    for group in section_01.groups:
        for subpoint in group.subpoints:
            jrn = subpoint.id
            if group.na_policy == "never":
                action, extra = "complete", {}
            else:
                action, extra = "not_applicable", {"not_applicable_reason": "Default is acceptable for this test"}
            resp = client.post(
                f"/api/v1/projects/{project['id']}/journey/items/{jrn}", json={"action": action, **extra}, headers=headers
            )
            assert resp.status_code == 200, (jrn, resp.text)

    journey = _journey(client, tenant, project["id"])
    assert _section(journey, "JRN-01")["status"] == "ready_to_continue"

    cont = client.post(f"/api/v1/projects/{project['id']}/journey/sections/JRN-01/continue", headers=headers)
    assert cont.status_code == 200, cont.text
    assert cont.json()["status"] == "completed"

    with_history = _journey(client, tenant, project["id"])
    assert _section(with_history, "JRN-01")["status"] == "ready_to_continue", "staying revisitable, not reset"
