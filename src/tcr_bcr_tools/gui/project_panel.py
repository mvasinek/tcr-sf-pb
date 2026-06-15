"""Project overview and status panels."""

from __future__ import annotations

import streamlit as st

from tcr_bcr_tools.gui.constants import FUTURE_ANALYSES
from tcr_bcr_tools.gui.helpers import build_status_rows
from tcr_bcr_tools.project import Project


def render_project_panel(project: Project) -> None:
    """Render project overview, status table, and future analyses."""
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

    _render_status_table(project)
    _render_available_analyses()


def _render_status_table(project: Project) -> None:
    st.markdown("### Status")
    status_map = project.get_status()
    if not isinstance(status_map, dict):
        status_map = {}
    rows = build_status_rows(status_map)
    st.table([{"Step": row["step"], "Status": row["display"]} for row in rows])
    for row in rows:
        st.markdown(f":{row['color']}[{row['step']}: {row['display']}]")


def _render_available_analyses() -> None:
    st.markdown("### 📊 Available analyses")
    for analysis in FUTURE_ANALYSES:
        st.markdown(f"- **{analysis}** — Coming in future release")
