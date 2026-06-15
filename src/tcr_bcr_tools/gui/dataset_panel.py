"""Dataset overview panel."""

from __future__ import annotations

import streamlit as st

from tcr_bcr_tools.project import Dataset


def render_dataset_panel(dataset: Dataset) -> None:
    """Render dataset metadata and directory information."""
    st.subheader("Dataset overview")
    meta = dataset.metadata()
    st.markdown(f"**Dataset ID:** {meta.get('id', dataset.dataset_id)}")
    st.markdown(f"**Source:** {meta.get('source', '')}")
    st.markdown(f"**Adapter:** {dataset.adapter()}")
    st.markdown(f"**Number of files:** {dataset.count_raw_files()}")
    st.markdown(f"**Raw directory:** `{dataset.raw_dir}`")
    st.markdown(f"**Intermediate directory:** `{dataset.intermediate_dir}`")

    raw_source = dataset.raw_source_path()
    if raw_source:
        st.markdown(f"**Registered raw source:** `{raw_source}`")

    if dataset.manifest_path.exists():
        st.markdown("**dataset.yaml** loaded.")
        st.json(dataset.load())
