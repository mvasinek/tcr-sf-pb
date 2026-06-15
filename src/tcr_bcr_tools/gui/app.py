"""Minimal Streamlit shell for workspace and project management."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from tcr_bcr_tools.project import Workspace

DEFAULT_WORKSPACE = Path.home() / "tcr-sf-pb-workspace"


def main() -> None:
    st.set_page_config(page_title="TCR SF/PB Analysis", layout="wide")
    st.title("TCR SF/PB Analysis")

    if "workspace_path" not in st.session_state:
        st.session_state.workspace_path = str(DEFAULT_WORKSPACE)

    workspace_path = st.sidebar.text_input(
        "Workspace path",
        value=st.session_state.workspace_path,
    )
    st.session_state.workspace_path = workspace_path

    workspace = Workspace(Path(workspace_path))
    workspace.load()

    projects = workspace.list_projects()
    datasets = workspace.list_datasets()
    default_project = workspace.settings.get("default_project", "")
    default_dataset = workspace.settings.get("default_dataset", "")

    selected_project = default_project if default_project in projects else ""
    if projects:
        selected_project = st.sidebar.selectbox(
            "Project",
            options=projects,
            index=projects.index(selected_project) if selected_project in projects else 0,
        )

    st.markdown("**Workspace:**")
    st.code(str(workspace.root))

    st.markdown("**Project:**")
    st.write(selected_project or "(none)")

    st.markdown("**Dataset:**")
    dataset_label = ", ".join(datasets) if datasets else default_dataset or "(none)"
    st.write(dataset_label)

    st.markdown("**Status:**")
    if selected_project:
        project = workspace.open_project(selected_project)
        status = project.get_status()
        if status:
            st.json(status)
        else:
            st.caption("No pipeline status recorded yet.")
    else:
        st.caption("Open a project to view status.")


if __name__ == "__main__":
    main()
