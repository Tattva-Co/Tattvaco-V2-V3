"""Script Ingestion & Assets."""

import streamlit as st

from apps.ui.api_client import TattvaApiClient
from apps.ui.components import safe_call


def render(client: TattvaApiClient, project: dict) -> None:
    st.header("Preserved Script Assets")
    st.write(
        "Upload screenplays into private immutable storage. Each asset is verified with a "
        "SHA-256 cryptographic digest before workflow processing."
    )

    uploaded_file = st.file_uploader(
        "Upload Screenplay (.fountain, .txt, .pdf)",
        type=["fountain", "txt", "pdf"],
    )
    if uploaded_file and st.button("Upload & Store Immutable Asset"):
        with st.spinner("Storing file in local storage and generating SHA-256 digest..."):
            res = safe_call(
                client.upload_asset,
                project["id"],
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "text/plain",
            )
            if res:
                st.success(f"Asset preserved! Checksum: `{res['checksum_sha256']}`")
                st.rerun()

    st.subheader("Existing Project Assets")
    assets = safe_call(client.list_assets, project["id"], default=[])
    if not assets:
        st.info("No script assets uploaded yet.")
        return
    for a in assets:
        with st.container():
            st.markdown(f"**📄 {a['filename']}** ({a['size_bytes']} bytes)")
            st.caption(
                f"SHA-256: `{a['checksum_sha256']}` | Path: `{a['storage_path']}` | Created: {a['created_at']}"
            )
            st.divider()
