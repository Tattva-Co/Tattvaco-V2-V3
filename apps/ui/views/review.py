"""Candidate Review & Approvals (human approval gate)."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call


def _render_approval_form(client: TattvaApiClient, approval: dict, scenes: list, entities: list) -> None:
    st.subheader(f"Pending Request: `{approval['id']}`")
    st.caption(f"Workflow Run: `{approval['workflow_run_id']}` | Scope: {approval['scope']}")

    # Only show candidates produced by this approval's workflow run.
    run_id = approval["workflow_run_id"]
    run_scenes = [s for s in scenes if s["workflow_run_id"] == run_id and s["status"] == "proposed"]
    run_entities = [e for e in entities if e["workflow_run_id"] == run_id and e["status"] == "proposed"]

    with st.form(f"approval_form_{approval['id']}"):
        st.markdown("### Proposed Scenes")
        selected_scenes = []
        for s in run_scenes:
            checked = st.checkbox(
                f"Scene {s['scene_number']}: {s['heading']} ({s['setting']} / {s['time_of_day']})",
                value=True,
                key=f"scene_{s['id']}",
            )
            st.caption(f"Summary: {s['summary']}")
            st.caption(f"Characters Present: {', '.join(s['characters_present']) or 'None'}")
            if checked:
                selected_scenes.append(s["id"])

        st.markdown("### Proposed Entities")
        selected_entities = []
        for e in run_entities:
            checked = st.checkbox(
                f"[{e['category'].upper()}] {e['name']} (Confidence: {int(e['confidence'] * 100)}%)",
                value=True,
                key=f"entity_{e['id']}",
            )
            if e.get("description"):
                st.caption(e["description"])
            if checked:
                selected_entities.append(e["id"])

        notes = st.text_input("Reviewer Notes", placeholder="Approved for production baseline")
        col_approve, col_reject = st.columns(2)
        with col_approve:
            approve_btn = st.form_submit_button("✅ Approve Selected Candidates")
        with col_reject:
            reject_btn = st.form_submit_button("❌ Reject All")

        if approve_btn:
            with st.spinner("Applying approval and advancing canonical project version..."):
                res = safe_call(
                    client.decide_approval, approval["id"], "approved", notes, selected_scenes, selected_entities
                )
                if res:
                    st.success(f"Approved! Project advanced to Version v{res['new_project_version']}")
                    st.rerun()

        if reject_btn:
            with st.spinner("Rejecting candidates..."):
                res = safe_call(client.decide_approval, approval["id"], "rejected", notes)
                if res:
                    st.warning("Candidates rejected.")
                    st.rerun()


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("Human Approval & Candidate Review Tray")
    st.write(
        "In accordance with Tattva Architectural Invariants, AI extraction yields candidates that "
        "require explicit human validation before promotion to the canonical project state."
    )

    data = safe_call(client.get_candidates, project["id"], default={}) or {}
    pending = [a for a in data.get("approvals", []) if a["status"] == "pending"]
    if not pending:
        st.success("✅ No pending approval requests. All candidates have either been reviewed or none are pending.")
        return
    for approval in pending:
        _render_approval_form(client, approval, data.get("scenes", []), data.get("entities", []))
