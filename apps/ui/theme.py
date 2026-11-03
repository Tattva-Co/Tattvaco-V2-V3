"""Workspace styling (Wireframe Spec visual tokens)."""

import streamlit as st

_CSS = """
<style>
.main { background-color: #0b0f19; color: #f3f4f6; }
.stMetric { background: rgba(30, 41, 59, 0.7); padding: 15px; border-radius: 10px; border: 1px solid #334155; }
.badge-version { background: #3b82f6; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
.badge-status { background: #10b981; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
.badge-pending { background: #f59e0b; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
.card { background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 16px; border: 1px solid #334155; }
.scene-heading { font-family: 'Courier New', Courier, monospace; font-weight: bold; color: #38bdf8; }
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
