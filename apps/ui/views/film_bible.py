"""Canonical Film Bible (System of Record & Visual World, Screen S-05)."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call

CATEGORY_LABELS = {
    "tone_aesthetic": "🎨 Tone & Aesthetic Direction",
    "color_palette": "🌈 Color Palette & Pigment Strategy",
    "lighting_atmosphere": "☀️ Lighting & Atmospheric Atmosphere",
    "architectural_environment": "🏛️ Architecture & Spatial Rules",
    "material_culture": "⚔️ Material Culture, Garments & Arms",
    "camera_language": "🎥 Camera Language & Cinematic Grammar",
}

STRICTNESS_BADGES = {
    "mandatory": "🔒 Mandatory (Strict Constraint)",
    "guideline": "💡 Creative Guideline",
    "deliberate_deviation": "⚡ Deliberate Historical Deviation",
}


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("📖 Canonical Film Bible (System of Record)")
    st.caption("Screen S-05 · Unified creative truth, visual-world rules & canonical project state")
    st.write(
        f"Authoritative project assets, world rules, and scenes committed to Version **v{project['current_version']}**. "
        "In accordance with Tattva Architectural Invariants: *Evidence before confidence* — "
        "visual rules ground cinematic generation and prompt synthesis."
    )

    tab_visual_world, tab_synthesis, tab_scenes, tab_entities, tab_versions = st.tabs([
        "🎨 Visual World Rules",
        "⚡ Synthesize Visual World (G-04)",
        "🎬 Canonical Scenes",
        "👥 Characters & Entities",
        "🏷️ Version History",
    ])

    # -------------------------------------------------------------------------
    # Tab 1: Visual World Rules (G-04 canonical rules)
    # -------------------------------------------------------------------------
    with tab_visual_world:
        st.subheader("Visual World Rules & Constraints")
        rules = safe_call(client.list_film_bible_rules, project["id"], default=[])

        col_rules, col_new = st.columns([2, 1])

        with col_rules:
            if not rules:
                st.info("No visual world rules committed yet. Run G-04 Film Bible Synthesis or create a rule on the right.")
            else:
                st.write(f"Total Canonical Rules: **{len(rules)}** · Project Version: **v{project['current_version']}**")
                for r in rules:
                    with st.container():
                        badge = STRICTNESS_BADGES.get(r["strictness"], r["strictness"])
                        cat_label = CATEGORY_LABELS.get(r["category"], r["category"].upper())
                        st.markdown(f"### {r['title']}")
                        st.caption(f"**{cat_label}** | `{badge}` | Version: v{r['project_version']}")
                        st.write(r["rule_text"])
                        if r.get("negative_prompt_guidance"):
                            st.warning(f"🚫 **Negative Prompt Guidance:** {r['negative_prompt_guidance']}")
                        if r.get("rationale"):
                            st.caption(f"💡 *Rationale:* {r['rationale']}")
                        st.divider()

        with col_new:
            st.markdown("#### Propose Manual Visual Rule")
            with st.form("manual_visual_rule_form"):
                cat = st.selectbox(
                    "Category",
                    list(CATEGORY_LABELS.keys()),
                    format_func=lambda k: CATEGORY_LABELS[k],
                )
                title = st.text_input("Rule Title", placeholder="e.g. Weathered Terracotta Glaze")
                rule_text = st.text_area("Rule Description", placeholder="Specify exact visual and material direction...")
                neg_guidance = st.text_input("Negative Prompt Guidance (Optional)", placeholder="e.g. glossy cgi, plastic sheen")
                strictness = st.selectbox(
                    "Strictness",
                    ["mandatory", "guideline", "deliberate_deviation"],
                    format_func=lambda s: STRICTNESS_BADGES[s],
                )
                submit_rule = st.form_submit_button("Add Rule to Canon")

            if submit_rule and title.strip() and rule_text.strip():
                with st.spinner("Recording visual world rule..."):
                    res = safe_call(
                        client.create_film_bible_rule,
                        project["id"],
                        cat,
                        title.strip(),
                        rule_text.strip(),
                        neg_guidance.strip() or None,
                        strictness,
                    )
                    if res:
                        st.success("Visual world rule added to canonical Film Bible!")
                        st.rerun()

    # -------------------------------------------------------------------------
    # Tab 2: Synthesize Visual World (G-04 Workflow)
    # -------------------------------------------------------------------------
    with tab_synthesis:
        st.subheader("Run Stateful Film Bible Synthesis (LangGraph G-04)")
        st.write(
            "Execute the Film Bible Synthesis graph: reads approved screenplay scenes and historical research claims, "
            "synthesizes structured aesthetic rules across tone, color, architecture, and lighting, "
            "evaluates potential historical contradictions via the Rule Conflict Detector, and opens a review gate."
        )

        with st.form("film_bible_workflow_form"):
            default_notes = f"Visual world for {project['title']} ({project.get('genre', 'Epic')})"
            user_notes = st.text_area(
                "Director Aesthetic Brief & World Notes",
                value=default_notes,
                placeholder="e.g. Gritty realism, terracotta and indigo palette, low dawn raking light, natural materials only.",
            )
            run_btn = st.form_submit_button("🚀 Run Film Bible Synthesis Graph")

        if run_btn:
            with st.spinner("Executing Film Bible Synthesis graph (Scenes + Claims -> Aesthetic Synthesis -> Conflict Check)..."):
                res = safe_call(client.run_film_bible_synthesis, project["id"], user_notes.strip() or None)
                if res:
                    st.success("Workflow executed up to human review gate!")
                    st.json(res)
                    st.info("👉 Switch to '🔍 Candidate Review & Approvals' to review and approve synthesized visual world rules.")

    # -------------------------------------------------------------------------
    # Tab 3: Canonical Scenes
    # -------------------------------------------------------------------------
    with tab_scenes:
        scenes = safe_call(client.list_scenes, project["id"], default=[])
        if not scenes:
            st.info("No canonical scenes committed yet.")
        for s in scenes:
            with st.expander(f"Scene {s['scene_number']}: {s['heading']} (v{s['project_version']})", expanded=True):
                st.markdown(
                    f"**Setting:** `{s['setting']}` | **Location:** `{s['location_name']}` | **Time:** `{s['time_of_day']}`"
                )
                st.write(s["summary"])
                st.markdown(f"**Characters:** {', '.join(s['characters_present']) if s['characters_present'] else 'None'}")
                st.caption(f"Source Locator: `{s['source_locator']}`")

    # -------------------------------------------------------------------------
    # Tab 4: Canonical Entities
    # -------------------------------------------------------------------------
    with tab_entities:
        entities = safe_call(client.list_entities, project["id"], default=[])
        if not entities:
            st.info("No canonical entities committed yet.")
        for e in entities:
            st.markdown(f"**[{e['category'].upper()}] {e['name']}** (v{e['project_version']})")
            if e.get("description"):
                st.write(e["description"])
            st.caption(f"Source Locator: `{e['source_locator']}`")
            st.divider()

    # -------------------------------------------------------------------------
    # Tab 5: Version History
    # -------------------------------------------------------------------------
    with tab_versions:
        for v in safe_call(client.list_versions, project["id"], default=[]):
            st.markdown(f"**Version {v['version_number']}** (`{v['branch_name']}`)")
            st.caption(f"Committed at: {v['created_at']} | Message: {v['commit_message']}")
            st.json(v["snapshot_data"])
            st.divider()
