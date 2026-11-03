"""Audit Trail & History."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("🛡️ Audit Trail & History")
    st.write("Complete audit log recording every project lifecycle action, approval event, and version change.")

    logs = safe_call(client.audit_log, project["id"], default=[])
    if not logs:
        st.info("No audit events recorded yet.")
        return
    for log in logs:
        with st.container():
            st.markdown(f"**{log['action'].upper()}** — Target: `{log['target_type']}` (`{log['target_id'][:8]}...`)")
            st.caption(f"Actor: `{log['actor_id']}` | Timestamp: `{log['created_at']}`")
            st.json(log["details"])
            st.divider()
