"""Tattva AI Film Director — desktop-first Streamlit workspace.

Run with: ``streamlit run apps/ui/app.py``

This module owns page setup, the sidebar (project selection, navigation, project
creation) and the header; each screen lives in ``apps/ui/views``.
"""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call
from apps.ui.theme import apply_theme
from apps.ui.views import NAVIGATION
from packages.core.config import get_settings

GENRES = ["Historical Epic", "Sci-Fi Thriller", "Mythological Fantasy", "Action / Drama"]


def _client() -> TattvaApiClient:
    settings = get_settings()
    return TattvaApiClient(settings.streamlit_api_base_url, timeout=settings.ui_request_timeout_seconds)


def _sidebar(client: TattvaApiClient):
    st.sidebar.title("🎬 Tattva AI Film Director")
    st.sidebar.caption("AI-Native Narrative Intelligence & Studio Workspace")

    projects = safe_call(client.list_projects, default=[])
    project_options = {p["title"]: p["id"] for p in projects}
    selected_title = st.sidebar.selectbox(
        "Active Project",
        options=list(project_options) if project_options else ["No Projects Available"],
    )
    project = None
    if selected_title in project_options:
        project = safe_call(client.get_project, project_options[selected_title])

    nav_selection = st.sidebar.radio("Studio Navigation", list(NAVIGATION))

    with st.sidebar.expander("➕ New Film Project"), st.form("new_project_form"):
        title = st.text_input("Project Title", placeholder="The Lost Dynasty")
        logline = st.text_area(
            "Logline", placeholder="A legendary warrior returns to protect their sacred heritage..."
        )
        genre = st.selectbox("Genre", GENRES)
        if st.form_submit_button("Create Project") and title:
            if safe_call(client.create_project, title, logline, genre):
                st.success(f"Project '{title}' created!")
                st.rerun()

    return project, nav_selection


def _header(project: dict) -> None:
    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
    with col1:
        st.subheader(f"🎞️ {project['title']}")
        if project.get("logline"):
            st.caption(project["logline"])
    col2.metric("Canonical Version", f"v{project['current_version']}")
    col3.metric("Status", project["status"].upper())
    col4.metric("Branch", "main")
    st.divider()


def main() -> None:
    st.set_page_config(
        page_title="Tattva AI Film Director",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()

    client = _client()
    project, nav_selection = _sidebar(client)
    if not project:
        st.info("👈 Please create or select a project in the sidebar to begin.")
        return

    _header(project)
    NAVIGATION[nav_selection].render(client, project)


main()
