"""Project overview and pipeline panels."""

from __future__ import annotations

import streamlit as st

from tcr_bcr_tools.gui.helpers import build_status_rows
from tcr_bcr_tools.gui.pipeline_panel import render_pipeline_panel
from tcr_bcr_tools.project import Project, Workspace


def render_project_panel(project: Project, workspace: Workspace) -> None:
    """Render project overview, status table, and pipeline execution."""
    data = project.manifest()
    project_meta = data.get("project", {})
    datasets = data.get("datasets", [])

    st.subheader("Project overview")
    st.markdown(f"**Project name:** {project_meta.get('name', project.project_id)}")
    st.markdown(f"**Description:** {project_meta.get('description', '')}")
    st.markdown(f"**Created:** {project_meta.get('created', '')}")
    st.markdown(f"**Modified:** {project_meta.get('modified', '')}")
    st.markdown(f"**Tool version:** {data.get('tool', {}).get('version', '')}")
    st.markdown(f"**Dataset:** {', '.join(datasets) if datasets else '(none)'}")
    st.markdown(f"**Adapter:** {data.get('adapter', '')}")

    if st.button("Open Results Browser", key="open_project_results"):
        st.session_state.show_results = True
        st.session_state.selected_results_analysis = ""

    _render_status_table(project)
    render_pipeline_panel(workspace, project)


def _render_status_table(project: Project) -> None:
    st.markdown("### Status")
    pipeline = project.manifest().get("pipeline", {})
    status_map = {
        step_id: str(state.get("status", "pending"))
        for step_id, state in pipeline.items()
        if isinstance(state, dict)
    }
    if not status_map:
        legacy = project.get_status()
        if isinstance(legacy, dict):
            status_map = legacy
    rows = build_status_rows(status_map)
    st.table([{"Step": row["step"], "Status": row["display"]} for row in rows])
