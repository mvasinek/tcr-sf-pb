"""Workspace summary panel."""

from __future__ import annotations

import streamlit as st

from tcr_bcr_tools import __version__
from tcr_bcr_tools.project import Workspace


def render_workspace_panel(workspace: Workspace) -> None:
    """Render workspace overview when no project is selected."""
    st.subheader("Workspace summary")
    st.markdown(f"**Workspace path:** `{workspace.root}`")
    st.markdown(f"**Number of datasets:** {len(workspace.list_datasets())}")
    st.markdown(f"**Number of projects:** {len(workspace.list_projects())}")
    st.markdown(f"**Tool version:** {__version__}")

    datasets = workspace.list_datasets()
    projects = workspace.list_projects()
    if datasets:
        st.markdown("**Datasets:** " + ", ".join(datasets))
    if projects:
        st.markdown("**Projects:** " + ", ".join(projects))
