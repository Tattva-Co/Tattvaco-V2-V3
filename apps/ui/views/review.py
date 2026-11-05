"""Candidate Review & Approvals (human approval gate)."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call


def _render_script_approval(client: TattvaApiClient, approval: dict, scenes: list, entities: list) -> None:
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
                    client.decide_approval,
                    approval["id"],
                    "approved",
                    notes,
                    scene_ids=selected_scenes,
                    entity_ids=selected_entities,
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


def _render_research_approval(client: TattvaApiClient, approval: dict, claims: list, questions: list) -> None:
    run_id = approval["workflow_run_id"]
    run_claims = [c for c in claims if c["workflow_run_id"] == run_id and c["status"] == "proposed"]
    run_questions = [q for q in questions if q["workflow_run_id"] == run_id and q["status"] == "proposed"]

    with st.form(f"research_approval_form_{approval['id']}"):
        st.markdown("### Proposed Historical Claims")
        selected_claims = []
        for c in run_claims:
            checked = st.checkbox(
                f"[{c['claim_class'].upper()}] {c['statement']}",
                value=True,
                key=f"claim_{c['id']}",
            )
            st.caption(
                f"Era: `{c.get('era_or_date') or 'Unspecified'}` | Source: `{c['source_title']}` ({c['source_tier']}) | Confidence: {int(c['confidence'] * 100)}%"
            )
            if checked:
                selected_claims.append(c["id"])

        st.markdown("### Proposed Open Questions")
        selected_questions = []
        for q in run_questions:
            checked = st.checkbox(
                f"[{q['category'].upper()}] {q['text']}",
                value=True,
                key=f"question_{q['id']}",
            )
            if checked:
                selected_questions.append(q["id"])

        notes = st.text_input("Reviewer Notes", placeholder="Approved historical claims and questions")
        col_approve, col_reject = st.columns(2)
        with col_approve:
            approve_btn = st.form_submit_button("✅ Approve Selected Research")
        with col_reject:
            reject_btn = st.form_submit_button("❌ Reject All")

        if approve_btn:
            with st.spinner("Applying approval and advancing canonical project version..."):
                res = safe_call(
                    client.decide_approval,
                    approval["id"],
                    "approved",
                    notes,
                    claim_ids=selected_claims,
                    question_ids=selected_questions,
                )
                if res:
                    st.success(f"Approved! Project advanced to Version v{res['new_project_version']}")
                    st.rerun()

        if reject_btn:
            with st.spinner("Rejecting research candidates..."):
                res = safe_call(client.decide_approval, approval["id"], "rejected", notes)
                if res:
                    st.warning("Research candidates rejected.")
                    st.rerun()


def _render_storyboard_approval(client: TattvaApiClient, approval: dict, panels: list) -> None:
    run_id = approval["workflow_run_id"]
    run_panels = [p for p in panels if p["workflow_run_id"] == run_id and p["status"] == "proposed"]

    with st.form(f"storyboard_approval_form_{approval['id']}"):
        st.markdown("### Proposed Storyboard Panels")
        selected_panels = []
        for p in run_panels:
            scene_str = f"Scene {p['suggested_scene_number']}" if p.get("suggested_scene_number") else "Sequence"
            checked = st.checkbox(
                f"Panel #{p['panel_number']} · [{p['shot_type'].upper()}] ({scene_str})",
                value=True,
                key=f"panel_{p['id']}",
            )
            st.caption(f"**Visual:** {p['description']}")
            if p.get("visual_notes"):
                st.caption(f"🎥 **Notes:** {p['visual_notes']}")
            if p.get("dialogue_snippet"):
                st.caption(f"💬 *\"{p['dialogue_snippet']}\"*")
            if checked:
                selected_panels.append(p["id"])

        notes = st.text_input("Reviewer Notes", placeholder="Approved storyboard panels for shot planning")
        col_approve, col_reject = st.columns(2)
        with col_approve:
            approve_btn = st.form_submit_button("✅ Approve Selected Panels")
        with col_reject:
            reject_btn = st.form_submit_button("❌ Reject All")

        if approve_btn:
            with st.spinner("Applying approval and advancing canonical project version..."):
                res = safe_call(
                    client.decide_approval,
                    approval["id"],
                    "approved",
                    notes,
                    panel_ids=selected_panels,
                )
                if res:
                    st.success(f"Approved! Project advanced to Version v{res['new_project_version']}")
                    st.rerun()

        if reject_btn:
            with st.spinner("Rejecting storyboard candidates..."):
                res = safe_call(client.decide_approval, approval["id"], "rejected", notes)
                if res:
                    st.warning("Storyboard candidates rejected.")
                    st.rerun()


def _render_film_bible_approval(client: TattvaApiClient, approval: dict, rules: list) -> None:
    run_id = approval["workflow_run_id"]
    run_rules = [r for r in rules if r["workflow_run_id"] == run_id and r["status"] == "proposed"]

    with st.form(f"film_bible_approval_form_{approval['id']}"):
        st.markdown("### Proposed Visual World Rules")
        selected_rules = []
        for r in run_rules:
            checked = st.checkbox(
                f"[{r['category'].upper()}] {r['title']} ({r['strictness']})",
                value=True,
                key=f"rule_{r['id']}",
            )
            st.write(r["rule_text"])
            if r.get("negative_prompt_guidance"):
                st.caption(f"🚫 Negative Prompt: `{r['negative_prompt_guidance']}`")
            if r.get("conflict_warning"):
                st.warning(f"⚠️ **Conflict Detected:** {r['conflict_warning']}")
            if checked:
                selected_rules.append(r["id"])

        notes = st.text_input("Reviewer Notes", placeholder="Approved visual world rules for project canon")
        col_approve, col_reject = st.columns(2)
        with col_approve:
            approve_btn = st.form_submit_button("✅ Approve Selected Rules")
        with col_reject:
            reject_btn = st.form_submit_button("❌ Reject All")

        if approve_btn:
            with st.spinner("Applying approval and advancing canonical project version..."):
                res = safe_call(
                    client.decide_approval,
                    approval["id"],
                    "approved",
                    notes,
                    rule_ids=selected_rules,
                )
                if res:
                    st.success(f"Approved! Project advanced to Version v{res['new_project_version']}")
                    st.rerun()

        if reject_btn:
            with st.spinner("Rejecting Film Bible candidates..."):
                res = safe_call(client.decide_approval, approval["id"], "rejected", notes)
                if res:
                    st.warning("Film Bible rules rejected.")
                    st.rerun()


def _render_approval_form(
    client: TattvaApiClient,
    approval: dict,
    scenes: list,
    entities: list,
    claims: list,
    questions: list,
    panels: list,
    rules: list,
) -> None:
    st.subheader(f"Pending Request: `{approval['id']}`")
    st.caption(f"Workflow Run: `{approval['workflow_run_id']}` | Scope: {approval['scope']}")

    if approval.get("scope") == "historical_research_candidates":
        _render_research_approval(client, approval, claims, questions)
    elif approval.get("scope") == "storyboard_candidates":
        _render_storyboard_approval(client, approval, panels)
    elif approval.get("scope") == "film_bible_rules":
        _render_film_bible_approval(client, approval, rules)
    else:
        _render_script_approval(client, approval, scenes, entities)


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
        _render_approval_form(
            client,
            approval,
            data.get("scenes", []),
            data.get("entities", []),
            data.get("research_claims", []),
            data.get("research_questions", []),
            data.get("storyboard_panels", []),
            data.get("film_bible_rules", []),
        )
