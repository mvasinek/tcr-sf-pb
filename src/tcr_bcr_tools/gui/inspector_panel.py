"""Inspector panel for selected project or dataset."""

from __future__ import annotations

import streamlit as st

from tcr_bcr_tools.project import Dataset, Project, Workspace


def render_inspector_panel(
    workspace: Workspace,
    selected_project: str,
    selected_dataset: str,
) -> None:
    """Render detail inspector for the current selection."""
    st.markdown("### Inspector")

    if selected_project:
        _render_project_inspector(workspace, selected_project)
    elif selected_dataset:
        _render_dataset_inspector(workspace, selected_dataset)
    else:
        st.caption("Select a project or dataset to inspect details.")


def _render_project_inspector(workspace: Workspace, project_id: str) -> None:
    project = workspace.open_project(project_id)
    st.markdown("#### 📂 Project")

    st.markdown("**Status**")
    status = project.get_status()
    if isinstance(status, dict) and status:
        st.json(status)
    else:
        st.caption("No status recorded.")

    st.markdown("**Files**")
    st.write(project.list_output_files() or ["(no outputs)"])

    st.markdown("**Outputs**")
    st.write(project.list_output_files() or ["(none)"])

    st.markdown("**Figures**")
    st.write(project.list_figure_files() or ["(none)"])


def _render_dataset_inspector(workspace: Workspace, dataset_id: str) -> None:
    dataset = workspace.open_dataset(dataset_id)
    st.markdown("#### 🧬 Dataset")

    st.markdown("**Metadata**")
    st.json(dataset.metadata())

    st.markdown("**Directories**")
    st.write(
        {
            "raw": str(dataset.raw_dir),
            "intermediate": str(dataset.intermediate_dir),
            "raw_source": str(dataset.raw_source_path() or ""),
        }
    )

    st.markdown("**Adapter**")
    st.write(dataset.adapter())
