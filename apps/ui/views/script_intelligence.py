"""Script Intelligence (G-01) trigger."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("⚡ Script Intelligence (Workflow G-01)")
    st.write(
        "Execute LangGraph stateful workflow to parse the screenplay, segment scenes, and extract "
        "characters and locations into candidate review."
    )

    assets = safe_call(client.list_assets, project["id"], default=[])
    if not assets:
        st.warning("Please upload a script asset under 'Script Ingestion & Assets' first.")
        return

    asset_options = {f"{a['filename']} ({a['id'][:8]}...)": a["id"] for a in assets}
    selected_label = st.selectbox("Select Script Asset for Extraction", list(asset_options.keys()))

    if st.button("🚀 Run Script Intelligence Graph"):
        with st.spinner("Executing LangGraph nodes (Parsing -> Candidate Extraction -> Approval Gate)..."):
            res = safe_call(client.run_script_intelligence, project["id"], asset_options[selected_label])
            if res:
                st.success("Workflow executed up to human review gate!")
                st.json(res)
                st.info("👉 Switch to 'Candidate Review & Approvals' to review and approve extracted scenes and entities.")
