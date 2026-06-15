"""Central results browser for project outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.io as pio
import streamlit as st

from tcr_bcr_tools.gui.constants import RESULTS_ANALYSES
from tcr_bcr_tools.gui.csv_viewer import filter_dataframe, load_csv_for_viewer, paginate_dataframe
from tcr_bcr_tools.gui.favorites import favorite_entries
from tcr_bcr_tools.gui.gallery import list_figure_entries, list_table_entries
from tcr_bcr_tools.gui.image_viewer import image_metadata
from tcr_bcr_tools.gui.json_viewer import load_json_data
from tcr_bcr_tools.gui.search import search_registry
from tcr_bcr_tools.gui.yaml_viewer import load_yaml_text
from tcr_bcr_tools.project.output_registry import OutputEntry, OutputRegistry
from tcr_bcr_tools.project import Project, Workspace


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def render_results_browser(workspace: Workspace, project: Project) -> None:
    """Render the full results browser for a project."""
    registry = project.output_registry(workspace.root)
    st.markdown("## Results Browser")

    tabs = st.tabs(
        [
            "Analysis",
            "Figures",
            "Tables",
            "Project Summary",
            "Compare",
            "Export",
        ]
    )

    with tabs[0]:
        _render_analysis_tab(registry, project)
    with tabs[1]:
        _render_figure_gallery(registry)
    with tabs[2]:
        _render_table_gallery(registry)
    with tabs[3]:
        _render_project_summary(registry, project)
    with tabs[4]:
        _render_compare_tab(registry)
    with tabs[5]:
        _render_export_tab(registry, project)


def _render_analysis_tab(registry: OutputRegistry, project: Project) -> None:
    analysis_key = st.session_state.get("selected_results_analysis", "")
    query = st.text_input("Search outputs", key="results_search_query")
    entries = search_registry(registry, query)
    if analysis_key and analysis_key != "reports":
        entries = registry.list_analysis_outputs(analysis_key)

    st.markdown("### Analysis overview")
    if analysis_key:
        step = project.get_pipeline_step(analysis_key)
        st.markdown(f"**Analysis:** {analysis_key}")
        st.markdown(f"**Status:** {step.get('status', 'pending')}")
        st.markdown(f"**Last execution:** {step.get('finished', '—')}")
        st.markdown(f"**Execution time:** {step.get('runtime', '—')}")
        st.markdown(f"**Tool version:** {step.get('version', '—')}")
    elif analysis_key == "reports":
        st.info("No reports available.")

    _render_output_table(registry, entries)
    selected_id = st.session_state.get("selected_output_id", "")
    if selected_id:
        entry = registry.find_output(selected_id)
        if entry:
            _render_preview(registry, entry)


def _render_output_table(registry: OutputRegistry, entries: list[OutputEntry]) -> None:
    st.markdown("### Outputs")
    if not entries:
        st.caption("No registered outputs.")
        return
    rows = []
    for entry in entries:
        rows.append(
            {
                "Name": entry.name,
                "Type": entry.type,
                "Size": _format_size(entry.size_bytes),
                "Created": entry.created,
                "id": entry.id,
            }
        )
    table = pd.DataFrame(rows)
    st.dataframe(table.drop(columns=["id"]), hide_index=True, use_container_width=True)

    options = {row["Name"]: row["id"] for row in rows}
    selected_name = st.selectbox("Select output", options=list(options.keys()))
    selected_id = options[selected_name]
    st.session_state["selected_output_id"] = selected_id

    cols = st.columns(4)
    if cols[0].button("Preview", key="preview_output"):
        registry.record_recent(selected_id)
    if cols[1].button("Refresh", key="refresh_outputs"):
        st.rerun()
    favorite = registry.is_favorite(selected_id)
    fav_label = "Unfavorite" if favorite else "Favorite"
    if cols[2].button(fav_label, key="toggle_favorite"):
        registry.favorite(selected_id, enabled=not favorite)
        st.rerun()
    if cols[3].button("Export current", key="export_current_output"):
        zip_path = registry.project_root / "cache" / f"{selected_id}.zip"
        registry.export_zip([selected_id], zip_path)
        st.success(f"Exported to {zip_path}")

    _render_recent(registry)
    _render_metadata(registry.find_output(selected_id))


def _render_recent(registry: OutputRegistry) -> None:
    st.markdown("### Last opened")
    recent = registry.recent()
    if not recent:
        st.caption("No recent outputs.")
        return
    for item in recent[:20]:
        entry = registry.find_output(str(item.get("id", "")))
        if entry:
            st.markdown(f"- `{entry.name}` ({item.get('opened', '')})")


def _render_metadata(entry: OutputEntry | None) -> None:
    if entry is None:
        return
    st.markdown("### Metadata")
    st.markdown(f"**Generated by:** {entry.pipeline_step or entry.analysis}")
    st.markdown(f"**Pipeline step:** {entry.pipeline_step}")
    st.markdown(f"**Tool version:** {entry.tool_version}")
    st.markdown(f"**Git commit:** {entry.git_commit}")
    st.markdown(f"**Git tag:** {entry.git_tag}")
    st.markdown(f"**Created:** {entry.created}")
    st.markdown(f"**Path:** `{entry.path}`")
    st.markdown(f"**Description:** {entry.description}")


def _render_preview(registry: OutputRegistry, entry: OutputEntry) -> None:
    st.markdown("### Preview")
    path = registry.resolve_path(entry)
    registry.record_recent(entry.id)
    if entry.type == "csv":
        _render_csv_preview(path)
    elif entry.type == "png":
        _render_image_preview(path, entry)
    elif entry.type == "html":
        _render_html_preview(path)
    elif entry.type == "yaml":
        st.code(load_yaml_text(path), language="yaml")
    elif entry.type == "json":
        if entry.name == "plotly.json":
            fig = pio.from_json(path.read_text(encoding="utf-8"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.json(load_json_data(path))
    elif entry.type == "directory":
        _render_directory_tree(path)
    else:
        st.code(path.read_text(encoding="utf-8"))


def _render_csv_preview(path: Path) -> None:
    df, truncated = load_csv_for_viewer(path)
    if truncated:
        st.warning(
            "Large CSV detected. Showing the first 5000 rows only."
        )
    query = st.text_input("Filter rows", key="csv_filter_query")
    columns = st.multiselect(
        "Columns",
        options=list(df.columns),
        default=list(df.columns),
        key="csv_filter_columns",
    )
    filtered = filter_dataframe(df, query=query, columns=columns)
    page = st.number_input("Page", min_value=1, value=1, step=1, key="csv_page")
    page_size = st.number_input("Page size", min_value=10, value=100, step=10, key="csv_page_size")
    page_df = paginate_dataframe(filtered, int(page), int(page_size))
    st.dataframe(page_df, use_container_width=True)
    st.download_button(
        "Download CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name=path.name,
        mime="text/csv",
    )


def _render_image_preview(path: Path, entry: OutputEntry) -> None:
    st.image(str(path))
    meta = image_metadata(path, entry)
    st.markdown(
        f"**Resolution:** {meta['resolution']}  \n"
        f"**Created:** {meta['created']}  \n"
        f"**Analysis:** {meta['analysis']}  \n"
        f"**Description:** {meta['description']}"
    )


def _render_html_preview(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    try:
        st.components.v1.html(html, height=600, scrolling=True)
    except Exception:  # noqa: BLE001 - fallback to external open message
        st.info("Open this HTML report in an external browser.")
        st.code(str(path))


def _render_directory_tree(path: Path) -> None:
    lines = [f"{path.name}/"]
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            rel = child.relative_to(path)
            indent = "  " * len(rel.parts)
            suffix = "/" if child.is_dir() else ""
            lines.append(f"{indent}{rel}{suffix}")
    st.code("\n".join(lines))


def _render_figure_gallery(registry: OutputRegistry) -> None:
    st.markdown("### Figure gallery")
    figures = list_figure_entries(registry)
    if not figures:
        st.caption("No figures registered.")
        return
    cols = st.columns(3)
    for index, entry in enumerate(figures):
        with cols[index % 3]:
            path = registry.resolve_path(entry)
            st.image(str(path), caption=entry.name)
            if st.button("Fullscreen", key=f"fullscreen_{entry.id}"):
                st.session_state["selected_output_id"] = entry.id
                st.image(str(path), use_container_width=True)


def _render_table_gallery(registry: OutputRegistry) -> None:
    st.markdown("### Table gallery")
    tables = list_table_entries(registry)
    if not tables:
        st.caption("No tables registered.")
        return
    for entry in tables:
        if st.button(entry.name, key=f"table_open_{entry.id}"):
            st.session_state["selected_output_id"] = entry.id
        path = registry.resolve_path(entry)
        df, truncated = load_csv_for_viewer(path)
        if truncated:
            st.caption(f"{entry.name}: showing first 5000 rows")
        st.dataframe(df.head(20), use_container_width=True)


def _render_project_summary(registry: OutputRegistry, project: Project) -> None:
    stats = registry.statistics()
    st.markdown("### Project Summary")
    cols = st.columns(3)
    cols[0].metric("Outputs", stats["outputs"])
    cols[1].metric("Figures", stats["figures"])
    cols[2].metric("Tables", stats["tables"])
    st.markdown(f"**Disk usage:** {_format_size(stats['disk_usage_bytes'])}")
    st.markdown(f"**Last execution:** {stats['last_execution'] or '—'}")
    st.markdown(f"**Tool version:** {stats['tool_version']}")

    manifest = project.manifest()
    st.markdown(f"**Dataset:** {', '.join(manifest.get('datasets', []))}")
    validation = manifest.get("validation", {})
    if validation:
        st.markdown(
            f"**Validation score:** {validation.get('score', '—')}/100 "
            f"({'valid' if validation.get('valid') else 'invalid'})"
        )
    pipeline = manifest.get("pipeline", {})
    completed = sum(
        1
        for state in pipeline.values()
        if isinstance(state, dict) and state.get("status") == "completed"
    )
    st.markdown(f"**Completed pipeline steps:** {completed}")
    favorites = favorite_entries(registry)
    st.markdown(f"**Favorites:** {len(favorites)}")


def _render_compare_tab(registry: OutputRegistry) -> None:
    entries = registry.list_outputs()
    if len(entries) < 2:
        st.caption("Need at least two outputs to compare.")
        return
    options = {entry.name: entry.id for entry in entries}
    left_name = st.selectbox("Output A", options=list(options.keys()), key="compare_output_a_name")
    right_name = st.selectbox("Output B", options=list(options.keys()), key="compare_output_b_name")
    left = registry.find_output(options[left_name])
    right = registry.find_output(options[right_name])
    if left is None or right is None:
        return
    col_a, col_b = st.columns(2)
    with col_a:
        _render_preview(registry, left)
    with col_b:
        _render_preview(registry, right)


def _render_export_tab(registry: OutputRegistry, project: Project) -> None:
    st.markdown("### Export")
    entries = registry.list_outputs()
    selected = st.multiselect(
        "Select outputs",
        options=[entry.id for entry in entries],
        format_func=lambda output_id: registry.find_output(output_id).name if registry.find_output(output_id) else output_id,
    )
    zip_path = project.cache_dir / "exports" / "selected_outputs.zip"
    if st.button("Export selected outputs"):
        registry.export_zip(selected, zip_path)
        st.success(f"Exported to {zip_path}")
    all_zip = project.cache_dir / "exports" / "all_outputs.zip"
    if st.button("Export all outputs"):
        registry.export_all_zip(all_zip)
        st.success(f"Exported to {all_zip}")


def render_results_sidebar_actions() -> None:
    """Render sidebar result analysis shortcuts."""
    st.sidebar.markdown("### 📊 Results")
    for label, key in RESULTS_ANALYSES:
        if st.sidebar.button(label, key=f"results_nav_{key}"):
            st.session_state.show_results = True
            st.session_state.selected_results_analysis = key
            st.session_state.selected_project = st.session_state.get("selected_project", "")
