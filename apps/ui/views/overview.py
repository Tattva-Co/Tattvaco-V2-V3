"""Project Overview."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("Project Intelligence Dashboard")
    st.write(
        "Welcome to the Tattva AI Film Director workspace. This modular monolith orchestrates "
        "screenplay parsing, semantic character extraction, scene breakdown, and human approval gating."
    )

    assets = safe_call(client.list_assets, project["id"], default=[])
    scenes = safe_call(client.list_scenes, project["id"], default=[])
    entities = safe_call(client.list_entities, project["id"], default=[])

    c1, c2, c3 = st.columns(3)
    c1.metric("Preserved Assets", len(assets))
    c2.metric("Approved Scenes", len(scenes))
    c3.metric("Approved Entities", len(entities))

    st.subheader("Project Attributes")
    st.json(
        {
            "project_id": project["id"],
            "organization_id": project["organization_id"],
            "genre": project.get("genre"),
            "created_at": project["created_at"],
            "updated_at": project["updated_at"],
        }
    )
