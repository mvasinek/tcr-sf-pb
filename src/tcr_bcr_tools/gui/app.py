"""TCR SF/PB Analysis — local Streamlit workspace manager."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from tcr_bcr_tools.gui.dataset_panel import render_dataset_panel
from tcr_bcr_tools.gui.inspector_panel import render_inspector_panel
from tcr_bcr_tools.gui.project_panel import render_project_panel
from tcr_bcr_tools.gui.session_state import init_session_state
from tcr_bcr_tools.gui.sidebar import render_sidebar
from tcr_bcr_tools.gui.status_bar import render_status_bar
from tcr_bcr_tools.gui.workspace_panel import render_workspace_panel
from tcr_bcr_tools.project import Workspace


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> None:
    st.set_page_config(
        page_title="TCR SF/PB Analysis",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session_state(st.session_state)

    st.title("TCR SF/PB Analysis")
    render_sidebar()

    workspace: Workspace = st.session_state.workspace
    selected_project = st.session_state.selected_project
    selected_dataset = st.session_state.selected_dataset

    main_col, inspector_col = st.columns([2.2, 1])

    with main_col:
        if st.session_state.get("show_settings"):
            st.info("Settings panel — coming in a future release.")
        elif st.session_state.get("show_logs"):
            st.info("Application logs — coming in a future release.")
        elif st.session_state.get("show_about"):
            st.markdown("Local bioinformatics IDE for TCR SF/PB analysis.")
        elif selected_dataset and not selected_project:
            dataset = workspace.open_dataset(selected_dataset)
            render_dataset_panel(dataset)
        elif selected_project:
            project = workspace.open_project(selected_project)
            render_project_panel(project, workspace)
        else:
            render_workspace_panel(workspace)

    with inspector_col:
        render_inspector_panel(workspace, selected_project, selected_dataset)

    render_status_bar(
        st.session_state.workspace_path,
        selected_project,
        selected_dataset,
        repo_root=_repo_root(),
    )


if __name__ == "__main__":
    main()
