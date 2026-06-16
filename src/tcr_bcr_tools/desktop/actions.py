"""Menu and toolbar action builders."""

from __future__ import annotations

from PySide6.QtGui import QAction


def build_file_actions(main_window) -> dict[str, QAction]:
    actions = {
        "new_workspace": QAction("New Workspace...", main_window),
        "open_workspace": QAction("Open Workspace...", main_window),
        "recent_workspaces": QAction("Recent Workspaces", main_window),
        "exit": QAction("Exit", main_window),
    }
    actions["exit"].setShortcut("Ctrl+Q")
    return actions


def build_project_actions(main_window) -> dict[str, QAction]:
    return {
        "new_project": QAction("New Project...", main_window),
        "open_project": QAction("Open Project...", main_window),
        "project_settings": QAction("Project Settings...", main_window),
    }


def build_dataset_actions(main_window) -> dict[str, QAction]:
    return {
        "register_dataset": QAction("Register Dataset...", main_window),
        "validate_dataset": QAction("Validate Dataset", main_window),
        "normalize_dataset": QAction("Normalize Dataset", main_window),
    }


def build_pipeline_actions(main_window) -> dict[str, QAction]:
    return {
        "run_step": QAction("Run Selected Step", main_window),
        "run_all": QAction("Run All", main_window),
        "stop": QAction("Stop", main_window),
    }


def build_view_actions(main_window) -> dict[str, QAction]:
    actions = {
        "workspace_explorer": QAction("Workspace Explorer", main_window),
        "inspector": QAction("Inspector", main_window),
        "logs": QAction("Logs", main_window),
        "results": QAction("Results", main_window),
    }
    for action in actions.values():
        action.setCheckable(True)
        action.setChecked(True)
    return actions


def build_help_actions(main_window) -> dict[str, QAction]:
    return {"about": QAction("About", main_window)}


def build_toolbar_actions(main_window) -> dict[str, QAction]:
    return {
        "open_workspace": QAction("Open Workspace", main_window),
        "new_project": QAction("New Project", main_window),
        "register_dataset": QAction("Register Dataset", main_window),
        "run_pipeline": QAction("Run Pipeline", main_window),
        "refresh": QAction("Refresh", main_window),
    }
