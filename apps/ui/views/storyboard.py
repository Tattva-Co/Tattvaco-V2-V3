"""Storyboard Studio (Workflow G-03, Screen S-02)."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call

SHOT_TYPE_LABELS = {
    "extreme_wide": "🌄 Extreme Wide Shot",
    "wide_establishing": "🏛️ Wide Establishing Shot",
    "medium_full": "🧍 Medium Full Shot",
    "medium_two_shot": "👥 Medium Two-Shot",
    "close_up": "🔍 Close-Up",
    "extreme_close_up": "👁️ Extreme Close-Up",
    "over_the_shoulder": "👤 Over-The-Shoulder",
    "low_angle_hero": "⚔️ Low-Angle Hero",
    "high_angle_bird": "🦅 High-Angle / Aerial",
    "dutch_angle": "📐 Dutch Angle",
    "insert_detail": "🔎 Insert / Detail",
}


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("🎨 Storyboard Studio (G-03)")
    st.caption("Screen S-02 · Visual sequence breakdown, shot alignment & beat boards")
    st.write(
        "Storyboard Intelligence breaks down approved script scenes and historical research "
        "into visual shot sequences with framing, camera angles, and visual notes. "
        "In accordance with Tattva Architectural Invariants, AI-generated panels must be reviewed and approved "
        "before committing to canonical project versions."
    )

    tab_board, tab_generate = st.tabs([
        "🎬 Sequence Board",
        "⚡ Run Storyboard Intelligence (G-03)",
    ])

    with tab_board:
        st.subheader("Canonical Storyboard Sequence")
        panels = safe_call(client.list_storyboard_panels, project["id"], default=[])

        if not panels:
            st.info("No canonical storyboard panels committed yet. Run the G-03 workflow to generate panel candidates.")
        else:
            st.write(f"Total Canonical Panels: **{len(panels)}** · Project Version: **v{project['current_version']}**")

            # Display panels in a 2-column visual grid
            cols = st.columns(2)
            for idx, p in enumerate(panels):
                col = cols[idx % 2]
                with col, st.container():
                    shot_label = SHOT_TYPE_LABELS.get(p["shot_type"], p["shot_type"].upper())
                    scene_info = f"Scene #{p['suggested_scene_number']}" if p.get("suggested_scene_number") else "Project Sequence"
                    st.markdown(
                        f"### Panel #{p['panel_number']} · `{shot_label}`"
                    )
                    st.caption(
                        f"**{scene_info}** | Aspect Ratio: `{p.get('aspect_ratio', '16:9')}` | Version: v{p['project_version']}"
                    )
                    st.markdown(f"**Visual Action:** {p['description']}")
                    if p.get("visual_notes"):
                        st.info(f"🎥 **Visual & Lighting Notes:** {p['visual_notes']}")
                    if p.get("dialogue_snippet"):
                        st.markdown(f"💬 *\"{p['dialogue_snippet']}\"*")
                    st.divider()

    with tab_generate:
        st.subheader("Run Stateful Storyboard Intelligence (LangGraph G-03)")
        st.write(
            "Execute the Storyboard Intelligence graph: reads approved scenes and historical claims, "
            "derives cinematographic shot framing, composes panel candidates, and opens a human review gate."
        )

        with st.form("storyboard_workflow_form"):
            default_brief = f"Cinematic storyboard sequence for {project['title']}"
            brief = st.text_area(
                "Director Visual Brief / Cinematography Intent",
                value=default_brief,
                placeholder="e.g. Gritty dawn lighting, wide establishing shot of Sisupalgarh ramparts, close-ups on bronze armor and worried expressions.",
            )
            run_btn = st.form_submit_button("🚀 Run Storyboard Intelligence Graph")

        if run_btn:
            with st.spinner("Executing Storyboard Intelligence graph (Aligning scenes & research -> Generating panel candidates)..."):
                res = safe_call(client.run_storyboard_intelligence, project["id"], brief.strip() or None)
                if res:
                    st.success("Workflow executed up to human review gate!")
                    st.json(res)
                    st.info("👉 Switch to '🔍 Candidate Review & Approvals' to review and approve proposed storyboard panels.")
