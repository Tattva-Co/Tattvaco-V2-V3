"""Tattva AI Film Director — Desktop-First Streamlit Workspace.

Provides the visual control center for project management, script ingestion,
LangGraph workflow execution, candidate review, human approval gating,
canonical film bible exploration, and audit logging.
"""

import os
from typing import Any, Dict, List, Optional
import requests
import streamlit as st

API_BASE_URL = os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="Tattva AI Film Director",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main { background-color: #0b0f19; color: #f3f4f6; }
    .stMetric { background: rgba(30, 41, 59, 0.7); padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    .badge-version { background: #3b82f6; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
    .badge-status { background: #10b981; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
    .badge-pending { background: #f59e0b; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
    .card { background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 16px; border: 1px solid #334155; }
    .scene-heading { font-family: 'Courier New', Courier, monospace; font-weight: bold; color: #38bdf8; }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(endpoint: str) -> Any:
    try:
        resp = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API Error ({endpoint}): {e}")
        return None


def api_post(endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Any:
    try:
        resp = requests.post(f"{API_BASE_URL}{endpoint}", json=data, files=files, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API Error ({endpoint}): {e}")
        return None


# ------------------------------------------------------------------------------
# Sidebar & Project Selection
# ------------------------------------------------------------------------------

st.sidebar.title("🎬 Tattva AI Film Director")
st.sidebar.caption("AI-Native Narrative Intelligence & Studio Workspace")

projects = api_get("/projects") or []
project_options = {p["title"]: p["id"] for p in projects}

selected_project_title = st.sidebar.selectbox(
    "Active Project",
    options=list(project_options.keys()) if project_options else ["No Projects Available"],
)

current_project = None
if project_options and selected_project_title in project_options:
    current_project = api_get(f"/projects/{project_options[selected_project_title]}")

nav_selection = st.sidebar.radio(
    "Studio Navigation",
    [
        "📽️ Project Overview",
        "📄 Script Ingestion & Assets",
        "⚡ Script Intelligence (G-01)",
        "🔍 Candidate Review & Approvals",
        "📖 Canonical Film Bible",
        "🛡️ Audit Trail & History",
    ],
)

# Project Creation Dialog
with st.sidebar.expander("➕ New Film Project"):
    with st.form("new_project_form"):
        new_title = st.text_input("Project Title", placeholder="The Lost Dynasty")
        new_logline = st.text_area("Logline", placeholder="A legendary warrior returns to protect their sacred heritage...")
        new_genre = st.selectbox("Genre", ["Historical Epic", "Sci-Fi Thriller", "Mythological Fantasy", "Action / Drama"])
        submitted = st.form_submit_button("Create Project")
        if submitted and new_title:
            res = api_post("/projects", {"title": new_title, "logline": new_logline, "genre": new_genre})
            if res:
                st.success(f"Project '{new_title}' created!")
                st.rerun()


# ------------------------------------------------------------------------------
# Main Header Bar
# ------------------------------------------------------------------------------

if current_project:
    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
    with col1:
        st.subheader(f"🎞️ {current_project['title']}")
        if current_project.get("logline"):
            st.caption(current_project["logline"])
    with col2:
        st.metric("Canonical Version", f"v{current_project['current_version']}")
    with col3:
        st.metric("Status", current_project["status"].upper())
    with col4:
        st.metric("Branch", "main")
    st.divider()
else:
    st.info("👈 Please create or select a project in the sidebar to begin.")


# ------------------------------------------------------------------------------
# View 1: Project Overview
# ------------------------------------------------------------------------------

if nav_selection == "📽️ Project Overview" and current_project:
    st.header("Project Intelligence Dashboard")
    st.write("Welcome to the Tattva AI Film Director workspace. This modular monolith orchestrates screenplay parsing, semantic character extraction, scene breakdown, and human approval gating.")

    c1, c2, c3 = st.columns(3)
    assets = api_get(f"/projects/{current_project['id']}/assets") or []
    scenes = api_get(f"/projects/{current_project['id']}/scenes") or []
    entities = api_get(f"/projects/{current_project['id']}/entities") or []

    with c1:
        st.metric("Preserved Assets", len(assets))
    with c2:
        st.metric("Approved Scenes", len(scenes))
    with c3:
        st.metric("Approved Entities", len(entities))

    st.subheader("Project Attributes")
    st.json({
        "project_id": current_project["id"],
        "organization_id": current_project["organization_id"],
        "genre": current_project.get("genre"),
        "created_at": current_project["created_at"],
        "updated_at": current_project["updated_at"],
    })


# ------------------------------------------------------------------------------
# View 2: Script Ingestion & Assets
# ------------------------------------------------------------------------------

elif nav_selection == "📄 Script Ingestion & Assets" and current_project:
    st.header("Preserved Script Assets")
    st.write("Upload screenplays into private immutable storage. Each asset is verified with a SHA-256 cryptographic digest before workflow processing.")

    uploaded_file = st.file_uploader(
        "Upload Screenplay (.fountain, .txt, .pdf)",
        type=["fountain", "txt", "pdf"],
    )

    if uploaded_file and st.button("Upload & Store Immutable Asset"):
        with st.spinner("Storing file in local storage and generating SHA-256 digest..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "text/plain")}
            res = api_post(f"/projects/{current_project['id']}/assets/upload", files=files)
            if res:
                st.success(f"Asset preserved! Checksum: `{res['checksum_sha256']}`")
                st.rerun()

    st.subheader("Existing Project Assets")
    assets = api_get(f"/projects/{current_project['id']}/assets") or []
    if assets:
        for a in assets:
            with st.container():
                st.markdown(f"**📄 {a['filename']}** ({a['size_bytes']} bytes)")
                st.caption(f"SHA-256: `{a['checksum_sha256']}` | Path: `{a['storage_path']}` | Created: {a['created_at']}")
                st.divider()
    else:
        st.info("No script assets uploaded yet.")


# ------------------------------------------------------------------------------
# View 3: Script Intelligence (G-01)
# ------------------------------------------------------------------------------

elif nav_selection == "⚡ Script Intelligence (G-01)" and current_project:
    st.header("⚡ Script Intelligence (Workflow G-01)")
    st.write("Execute LangGraph stateful workflow to parse the screenplay, segment scenes, and extract characters and locations into candidate review.")

    assets = api_get(f"/projects/{current_project['id']}/assets") or []
    if not assets:
        st.warning("Please upload a script asset under 'Script Ingestion & Assets' first.")
    else:
        asset_options = {f"{a['filename']} ({a['id'][:8]}...)": a["id"] for a in assets}
        selected_asset_label = st.selectbox("Select Script Asset for Extraction", list(asset_options.keys()))
        selected_asset_id = asset_options[selected_asset_label]

        if st.button("🚀 Run Script Intelligence Graph"):
            with st.spinner("Executing LangGraph nodes (Parsing -> Candidate Extraction -> Approval Gate)..."):
                res = api_post(
                    f"/projects/{current_project['id']}/workflows/script-intelligence",
                    data={"script_asset_id": selected_asset_id, "sync_execution": True},
                )
                if res:
                    st.success("Workflow executed up to human review gate!")
                    st.json(res)
                    st.info("👉 Switch to 'Candidate Review & Approvals' to review and approve extracted scenes and entities.")


# ------------------------------------------------------------------------------
# View 4: Candidate Review & Approvals
# ------------------------------------------------------------------------------

elif nav_selection == "🔍 Candidate Review & Approvals" and current_project:
    st.header("Human Approval & Candidate Review Tray")
    st.write("In accordance with Tattva Architectural Invariants, AI extraction yields candidates that require explicit human validation before promotion to the canonical project state.")

    candidates_data = api_get(f"/projects/{current_project['id']}/candidates") or {}
    scenes = candidates_data.get("scenes", [])
    entities = candidates_data.get("entities", [])
    approvals = candidates_data.get("approvals", [])

    pending_approvals = [a for a in approvals if a["status"] == "pending"]

    if not pending_approvals:
        st.success("✅ No pending approval requests. All candidates have either been reviewed or none are pending.")
    else:
        for apprv in pending_approvals:
            st.subheader(f"Pending Request: `{apprv['id']}`")
            st.caption(f"Workflow Run: `{apprv['workflow_run_id']}` | Scope: {apprv['scope']}")

            with st.form(f"approval_form_{apprv['id']}"):
                st.markdown("### Proposed Scenes")
                selected_scenes = []
                for s in scenes:
                    if s["status"] == "proposed":
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
                for e in entities:
                    if e["status"] == "proposed":
                        checked = st.checkbox(
                            f"[{e['category'].upper()}] {e['name']} (Confidence: {int(e['confidence']*100)}%)",
                            value=True,
                            key=f"entity_{e['id']}",
                        )
                        if e.get("description"):
                            st.caption(e["description"])
                        if checked:
                            selected_entities.append(e["id"])

                notes = st.text_input("Reviewer Notes", placeholder="Approved for production baseline")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    approve_btn = st.form_submit_button("✅ Approve Selected Candidates")
                with col_btn2:
                    reject_btn = st.form_submit_button("❌ Reject All")

                if approve_btn:
                    with st.spinner("Applying approval and advancing canonical project version..."):
                        res = api_post(
                            f"/approvals/{apprv['id']}/decide",
                            data={
                                "decision": "approved",
                                "actor_id": current_project["created_by"],
                                "notes": notes,
                                "approved_scene_ids": selected_scenes,
                                "approved_entity_ids": selected_entities,
                            },
                        )
                        if res:
                            st.success(f"Approved! Project advanced to Version v{res['new_project_version']}")
                            st.rerun()

                if reject_btn:
                    with st.spinner("Rejecting candidates..."):
                        res = api_post(
                            f"/approvals/{apprv['id']}/decide",
                            data={
                                "decision": "rejected",
                                "actor_id": current_project["created_by"],
                                "notes": notes,
                            },
                        )
                        if res:
                            st.warning("Candidates rejected.")
                            st.rerun()


# ------------------------------------------------------------------------------
# View 5: Canonical Film Bible & Scenes
# ------------------------------------------------------------------------------

elif nav_selection == "📖 Canonical Film Bible" and current_project:
    st.header("📖 Canonical Film Bible (System of Record)")
    st.write(f"Authoritative project entities and scenes committed to Version **v{current_project['current_version']}**.")

    tab_scenes, tab_entities, tab_versions = st.tabs(["🎬 Canonical Scenes", "👥 Characters & Entities", "🏷️ Version History"])

    with tab_scenes:
        scenes = api_get(f"/projects/{current_project['id']}/scenes") or []
        if scenes:
            for s in scenes:
                with st.expander(f"Scene {s['scene_number']}: {s['heading']} (v{s['project_version']})", expanded=True):
                    st.markdown(f"**Setting:** `{s['setting']}` | **Location:** `{s['location_name']}` | **Time:** `{s['time_of_day']}`")
                    st.write(s["summary"])
                    st.markdown(f"**Characters:** {', '.join(s['characters_present']) if s['characters_present'] else 'None'}")
                    st.caption(f"Source Locator: `{s['source_locator']}`")
        else:
            st.info("No canonical scenes committed yet.")

    with tab_entities:
        entities = api_get(f"/projects/{current_project['id']}/entities") or []
        if entities:
            for e in entities:
                st.markdown(f"**[{e['category'].upper()}] {e['name']}** (v{e['project_version']})")
                if e.get("description"):
                    st.write(e["description"])
                st.caption(f"Source Locator: `{e['source_locator']}`")
                st.divider()
        else:
            st.info("No canonical entities committed yet.")

    with tab_versions:
        versions = api_get(f"/projects/{current_project['id']}/versions") or []
        for v in versions:
            st.markdown(f"**Version {v['version_number']}** (`{v['branch_name']}`)")
            st.caption(f"Committed at: {v['created_at']} | Message: {v['commit_message']}")
            st.json(v["snapshot_data"])
            st.divider()


# ------------------------------------------------------------------------------
# View 6: Audit Trail & History
# ------------------------------------------------------------------------------

elif nav_selection == "🛡️ Audit Trail & History" and current_project:
    st.header("🛡️ Tamper-Evident Audit Trail")
    st.write("Complete immutable audit log recording every project lifecycle action, approval event, and version change.")

    audit_logs = api_get(f"/projects/{current_project['id']}/audit-log") or []
    if audit_logs:
        for log in audit_logs:
            with st.container():
                st.markdown(f"**{log['action'].upper()}** — Target: `{log['target_type']}` (`{log['target_id'][:8]}...`)")
                st.caption(f"Actor: `{log['actor_id']}` | Timestamp: `{log['created_at']}`")
                st.json(log["details"])
                st.divider()
    else:
        st.info("No audit events recorded yet.")
