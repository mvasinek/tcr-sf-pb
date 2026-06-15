"""Minimal Streamlit shell for workspace and project management."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

DEFAULT_WORKSPACE = Path.home() / "tcr-sf-pb-workspace"


def _list_projects(workspace: Path) -> list[str]:
    projects_dir = workspace / "projects"
    if not projects_dir.is_dir():
        return []
    return sorted(
        item.name
        for item in projects_dir.iterdir()
        if item.is_dir() and (item / "project.yaml").exists()
    )


def _project_outputs(project_name: str, workspace: Path) -> list[str]:
    outputs_dir = workspace / "projects" / project_name / "outputs"
    if not outputs_dir.is_dir():
        return []
    return sorted(path.name for path in outputs_dir.rglob("*") if path.is_file())


def main() -> None:
    st.set_page_config(page_title="TCR SF/PB Analysis", layout="wide")
    st.title("TCR SF/PB Analysis")

    if "workspace_path" not in st.session_state:
        st.session_state.workspace_path = str(DEFAULT_WORKSPACE)

    with st.sidebar:
        st.header("Workspace")
        workspace_input = st.text_input(
            "Workspace path",
            value=st.session_state.workspace_path,
            help="Root directory containing datasets/ and projects/.",
        )
        st.session_state.workspace_path = workspace_input
        workspace = Path(workspace_input)

        st.divider()
        st.header("Project")

        projects = _list_projects(workspace)
        selected_project = st.selectbox(
            "Project selector",
            options=[""] + projects,
            format_func=lambda value: value or "(none selected)",
        )

        if st.button("Create project", use_container_width=True):
            st.info("Project creation will be available in v0.5.0.")

        if st.button("Open project", use_container_width=True, disabled=not selected_project):
            st.session_state.open_project = selected_project

    open_project = st.session_state.get("open_project") or selected_project

    st.subheader("Project overview")
    if not open_project:
        st.write("Select or create a project to view its overview.")
    else:
        project_dir = workspace / "projects" / open_project
        st.markdown(f"**Project:** `{open_project}`")
        st.markdown(f"**Path:** `{project_dir}`")
        manifest = project_dir / "project.yaml"
        if manifest.exists():
            st.success("`project.yaml` found.")
        else:
            st.warning("`project.yaml` not found.")

    st.subheader("Available outputs")
    if not open_project:
        st.caption("Outputs will appear here after analyses are run.")
    else:
        outputs = _project_outputs(open_project, workspace)
        if outputs:
            st.write(outputs)
        else:
            st.caption("No output files yet.")

    st.subheader("Logs")
    if not open_project:
        st.caption("Run logs will appear here.")
    else:
        logs_dir = workspace / "projects" / open_project / "logs"
        if logs_dir.is_dir():
            log_files = sorted(path.name for path in logs_dir.iterdir() if path.is_file())
            st.write(log_files or "No log files yet.")
        else:
            st.caption("Logs directory not created yet.")


if __name__ == "__main__":
    main()
