"""Sidebar navigation and workspace controls."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from tcr_bcr_tools import __version__
from tcr_bcr_tools.gui.constants import ADAPTER_OPTIONS
from tcr_bcr_tools.gui.dialogs import create_project_from_dialog, register_dataset_from_dialog
from tcr_bcr_tools.gui.results_browser import render_results_sidebar_actions
from tcr_bcr_tools.project import Workspace


def render_sidebar() -> None:
    """Render sidebar sections and update session state."""
    st.sidebar.markdown("### 📁 Workspace")
    workspace_path = st.sidebar.text_input(
        "Workspace path",
        value=st.session_state.workspace_path,
        key="sidebar_workspace_path",
    )
    st.session_state.workspace_path = workspace_path
    st.sidebar.caption(f"Current version: {__version__}")

    col_open, col_create = st.sidebar.columns(2)
    with col_open:
        if st.button("Open workspace", use_container_width=True):
            workspace = Workspace(Path(workspace_path))
            workspace.load()
            st.session_state.workspace = workspace
    with col_create:
        if st.button("Create workspace", use_container_width=True):
            workspace = Workspace(Path(workspace_path))
            workspace.load()
            st.session_state.workspace = workspace
            st.sidebar.success("Workspace ready.")

    workspace: Workspace | None = st.session_state.get("workspace")
    if workspace is None:
        workspace = Workspace(Path(workspace_path))
        workspace.load()
        st.session_state.workspace = workspace

    st.sidebar.divider()
    st.sidebar.markdown("### 📂 Projects")
    projects = workspace.list_projects()
    for project_id in projects:
        marker = "●" if project_id == st.session_state.selected_project else "○"
        if st.sidebar.button(f"{marker} {project_id}", key=f"project_select_{project_id}"):
            st.session_state.selected_project = project_id
            st.session_state.selected_dataset = ""

    btn_cols = st.sidebar.columns(2)
    with btn_cols[0]:
        if st.button("New project", use_container_width=True):
            st.session_state.show_create_project = True
    with btn_cols[1]:
        if st.button("Open", use_container_width=True, disabled=not st.session_state.selected_project):
            pass
    btn_cols2 = st.sidebar.columns(2)
    with btn_cols2[0]:
        if st.button("Delete", use_container_width=True, disabled=not st.session_state.selected_project):
            workspace.delete_project(st.session_state.selected_project)
            st.session_state.selected_project = ""
    with btn_cols2[1]:
        if st.button("Refresh", use_container_width=True, key="refresh_projects"):
            st.rerun()

    st.sidebar.divider()
    st.sidebar.markdown("### 🧬 Datasets")
    datasets = workspace.list_datasets()
    for dataset_id in datasets:
        marker = "●" if dataset_id == st.session_state.selected_dataset else "○"
        if st.sidebar.button(f"{marker} {dataset_id}", key=f"dataset_select_{dataset_id}"):
            st.session_state.selected_dataset = dataset_id
            st.session_state.selected_project = ""

    ds_cols = st.sidebar.columns(2)
    with ds_cols[0]:
        if st.button("Add dataset", use_container_width=True):
            st.session_state.show_register_dataset = True
    with ds_cols[1]:
        if st.button("Refresh", use_container_width=True, key="refresh_datasets"):
            st.rerun()
    if st.sidebar.button("Show metadata", use_container_width=True, disabled=not st.session_state.selected_dataset):
        st.session_state.show_dataset_overview = True

    st.sidebar.divider()
    render_results_sidebar_actions()

    st.sidebar.divider()
    st.sidebar.markdown("### Application")
    if st.sidebar.button("⚙ Settings"):
        st.session_state.show_settings = True
    if st.sidebar.button("📜 Logs"):
        st.session_state.show_logs = True
    if st.sidebar.button("About"):
        st.session_state.show_about = True

    _render_create_project_dialog(workspace, datasets)
    _render_register_dataset_dialog(workspace)


def _render_create_project_dialog(workspace: Workspace, datasets: list[str]) -> None:
    if not st.session_state.get("show_create_project"):
        return
    with st.sidebar.expander("Create Project", expanded=True):
        name = st.text_input("Project name", key="create_project_name")
        description = st.text_input("Description", key="create_project_description")
        dataset = st.selectbox(
            "Dataset",
            options=[""] + datasets,
            format_func=lambda value: value or "(none)",
            key="create_project_dataset",
        )
        adapter = st.selectbox("Adapter", options=ADAPTER_OPTIONS, key="create_project_adapter")
        if st.button("Create", key="confirm_create_project"):
            if name.strip():
                project = create_project_from_dialog(
                    workspace,
                    name=name.strip(),
                    description=description.strip(),
                    dataset_id=dataset,
                    adapter=adapter,
                )
                st.session_state.selected_project = project.project_id
                st.session_state.show_create_project = False
                st.rerun()
        if st.button("Cancel", key="cancel_create_project"):
            st.session_state.show_create_project = False
            st.rerun()


def _render_register_dataset_dialog(workspace: Workspace) -> None:
    if not st.session_state.get("show_register_dataset"):
        return
    with st.sidebar.expander("Register dataset", expanded=True):
        dataset_id = st.text_input("Dataset ID", key="register_dataset_id")
        source = st.text_input("Source", key="register_dataset_source")
        adapter = st.selectbox("Adapter", options=ADAPTER_OPTIONS, key="register_dataset_adapter")
        raw_directory = st.text_input("Raw directory", key="register_dataset_raw")
        if st.button("Register", key="confirm_register_dataset"):
            if dataset_id.strip():
                register_dataset_from_dialog(
                    workspace,
                    dataset_id=dataset_id.strip(),
                    source=source.strip(),
                    adapter=adapter,
                    raw_directory=raw_directory.strip(),
                )
                st.session_state.selected_dataset = dataset_id.strip()
                st.session_state.show_register_dataset = False
                st.rerun()
        if st.button("Cancel", key="cancel_register_dataset"):
            st.session_state.show_register_dataset = False
            st.rerun()
