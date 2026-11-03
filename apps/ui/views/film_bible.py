"""Canonical Film Bible (system of record)."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("📖 Canonical Film Bible (System of Record)")
    st.write(f"Authoritative project entities and scenes committed to Version **v{project['current_version']}**.")

    tab_scenes, tab_entities, tab_versions = st.tabs(
        ["🎬 Canonical Scenes", "👥 Characters & Entities", "🏷️ Version History"]
    )

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

    with tab_versions:
        for v in safe_call(client.list_versions, project["id"], default=[]):
            st.markdown(f"**Version {v['version_number']}** (`{v['branch_name']}`)")
            st.caption(f"Committed at: {v['created_at']} | Message: {v['commit_message']}")
            st.json(v["snapshot_data"])
            st.divider()
