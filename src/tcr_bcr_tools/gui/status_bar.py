"""Application status bar."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from tcr_bcr_tools import __version__
from tcr_bcr_tools.gui.git_info import get_git_summary


def render_status_bar(
    workspace_path: str,
    selected_project: str,
    selected_dataset: str,
    repo_root: Path | None = None,
) -> None:
    """Render bottom status bar with workspace and Git info."""
    git_info = get_git_summary(repo_root)
    st.divider()
    cols = st.columns(5)
    cols[0].caption(f"Workspace: {workspace_path}")
    cols[1].caption(f"Project: {selected_project or '(none)'}")
    cols[2].caption(f"Dataset: {selected_dataset or '(none)'}")
    cols[3].caption(f"Tool: {__version__}")
    if git_info["available"] == "true":
        cols[4].caption(
            f"Git: {git_info['branch']} | {git_info['commit']} | {git_info['tag']}"
        )
    else:
        cols[4].caption("Git: unavailable")
