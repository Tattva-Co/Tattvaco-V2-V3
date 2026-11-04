"""Historical Research & Cultural Verification (Workflow G-02, Screens P-09/P-10)."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call

TIER_LABELS = {
    "tier_0_project": "Tier 0 (Project Material)",
    "tier_1_primary": "Tier 1 (Primary / Archaeological)",
    "tier_2_scholarly": "Tier 2 (Scholarly Secondary)",
    "tier_3_discovery": "Tier 3 (Discovery / Unverified)",
}

CLAIM_CLASS_LABELS = {
    "historical_fact": "🏛️ Historical Fact",
    "historical_interpretation": "🔍 Interpretation",
    "contested_claim": "⚡ Contested Claim",
    "creative_dramatization": "🎭 Creative Dramatization",
    "user_assertion": "📝 User Assertion",
    "unverified": "❓ Unverified",
}


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("🏛️ Historical Research & Cultural Verification (G-02)")
    st.caption("Screens P-09 & P-10 · Grounding visual world & narrative chronology in traceable evidence")
    st.write(
        "Establish an evidence-backed understanding of the historical period, geography, polity, "
        "and material culture. In accordance with Tattva Architectural Invariants: *Evidence before confidence* "
        "— claims without evidence remain unverified."
    )

    tab_investigate, tab_questions, tab_sources, tab_claims, tab_conflicts = st.tabs([
        "🔬 Launch Investigation (G-02)",
        "❓ Open Questions",
        "📚 Source Library",
        "📜 Evidence & Claims",
        "⚡ Conflicts & Disputes",
    ])

    # -------------------------------------------------------------------------
    # Tab 1: Launch Research Workflow G-02
    # -------------------------------------------------------------------------
    with tab_investigate:
        st.subheader("Run Stateful Research Workflow (LangGraph G-02)")
        st.write(
            "Execute an autonomous investigation loop that retrieves primary/scholarly sources, "
            "extracts claims with locators, detects contested interpretations, and opens a review gate."
        )

        with st.form("research_workflow_form"):
            default_topic = f"{project.get('genre', 'Historical')} era for {project['title']}"
            topic = st.text_input("Investigation Topic or Subject", value=default_topic)
            seed_text = st.text_area(
                "Director Notes / Specific Query (Optional)",
                placeholder="e.g. Focus on military attire, armor materials, and Sisupalgarh brick ramparts c. 261 BCE",
            )
            run_btn = st.form_submit_button("🚀 Run Historical Investigation Graph")

        if run_btn and topic.strip():
            with st.spinner("Executing Historical Research graph (Intake -> Source Analysis -> Candidate Extraction)..."):
                res = safe_call(client.run_historical_research, project["id"], topic.strip(), seed_text.strip() or None)
                if res:
                    st.success("Workflow executed up to human review gate!")
                    st.json(res)
                    st.info("👉 Switch to '🔍 Candidate Review & Approvals' to review and approve extracted claims and questions.")

    # -------------------------------------------------------------------------
    # Tab 2: Open Questions (P-09)
    # -------------------------------------------------------------------------
    with tab_questions:
        st.subheader("Historical Inquiries & Open Questions")
        questions = safe_call(client.list_research_questions, project["id"], default=[])

        col_q1, col_q2 = st.columns([2, 1])
        with col_q1:
            if not questions:
                st.info("No research questions logged yet. Add one below or run the G-02 workflow.")
            else:
                for q in questions:
                    with st.container():
                        st.markdown(f"**[{q['category'].upper()}]** {q['text']}")
                        st.caption(f"Status: `{q['status']}` | Version: v{q['project_version']} | Added: {q['created_at']}")
                        st.divider()

        with col_q2:
            st.markdown("#### Propose New Question")
            with st.form("new_question_form"):
                q_text = st.text_input("Question Text")
                q_cat = st.selectbox(
                    "Category",
                    ["general", "costume", "architecture", "military", "politics", "religion", "trade"],
                )
                if st.form_submit_button("Add Question") and q_text.strip():
                    if safe_call(client.create_research_question, project["id"], q_text.strip(), q_cat):
                        st.success("Question recorded!")
                        st.rerun()

    # -------------------------------------------------------------------------
    # Tab 3: Sources (P-10)
    # -------------------------------------------------------------------------
    with tab_sources:
        st.subheader("Traceable Bibliographic & Archaeological Sources")
        sources = safe_call(client.list_research_sources, project["id"], default=[])

        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            if not sources:
                st.info("No sources recorded yet. Register a primary or secondary source below.")
            else:
                for s in sources:
                    tier_badge = TIER_LABELS.get(s["tier"], s["tier"])
                    with st.expander(f"{s['title']} ({tier_badge})", expanded=True):
                        if s.get("author"):
                            st.markdown(f"**Author / Authority:** {s['author']} ({s.get('publication_year') or 'n.d.'})")
                        if s.get("locator"):
                            st.markdown(f"**Locator / Citation:** `{s['locator']}`")
                        if s.get("reliability_notes"):
                            st.caption(f"Reliability: {s['reliability_notes']}")
                        st.caption(f"Committed to Version: v{s['project_version']}")

        with col_s2:
            st.markdown("#### Register Canonical Source")
            with st.form("new_source_form"):
                s_title = st.text_input("Source Title")
                s_tier = st.selectbox("Source Tier", list(TIER_LABELS.keys()), format_func=lambda k: TIER_LABELS[k])
                s_author = st.text_input("Author / Authority (optional)")
                s_locator = st.text_input("Citation Locator (e.g. Vol. I, p. 45)")
                if st.form_submit_button("Record Source") and s_title.strip():
                    if safe_call(
                        client.create_research_source,
                        project["id"],
                        s_title.strip(),
                        tier=s_tier,
                        author=s_author.strip() or None,
                        locator=s_locator.strip() or None,
                    ):
                        st.success("Source preserved in project truth!")
                        st.rerun()

    # -------------------------------------------------------------------------
    # Tab 4: Canonical Claims & Findings
    # -------------------------------------------------------------------------
    with tab_claims:
        st.subheader("Approved Evidence-Grounded Claims")
        claims = safe_call(client.list_research_claims, project["id"], default=[])
        if not claims:
            st.info("No canonical claims committed yet. Run G-02 and approve candidate claims in the Review Tray.")
        else:
            for c in claims:
                class_label = CLAIM_CLASS_LABELS.get(c["claim_class"], c["claim_class"])
                with st.container():
                    st.markdown(f"**{class_label}** — {c['statement']}")
                    meta = []
                    if c.get("era_or_date"):
                        meta.append(f"Era: `{c['era_or_date']}`")
                    if c.get("location"):
                        meta.append(f"Location: `{c['location']}`")
                    meta.append(f"Confidence: `{int(c['confidence'] * 100)}%`")
                    meta.append(f"Version: `v{c['project_version']}`")
                    st.caption(" | ".join(meta))
                    st.divider()

    # -------------------------------------------------------------------------
    # Tab 5: Conflicts & Disputes
    # -------------------------------------------------------------------------
    with tab_conflicts:
        st.subheader("Contested Claims & Historical Contradictions")
        conflicts = safe_call(client.list_research_conflicts, project["id"], default=[])
        if not conflicts:
            st.success("✅ No open historical conflicts or contradictions flagged for this project.")
        else:
            for conf in conflicts:
                with st.expander(f"Dispute: {conf['description'][:60]}...", expanded=True):
                    st.write(conf["description"])
                    if conf.get("resolution_notes"):
                        st.info(f"Resolution Stance: {conf['resolution_notes']}")
                    st.caption(f"Status: `{conf['status']}` | Version: v{conf['project_version']}")

