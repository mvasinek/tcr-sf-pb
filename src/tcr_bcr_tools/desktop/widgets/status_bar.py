"""Application status bar widget."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QStatusBar

from tcr_bcr_tools import __version__
from tcr_bcr_tools.desktop.state import DesktopState
from tcr_bcr_tools.git_info import get_git_summary


class AppStatusBar(QStatusBar):
    """Status bar showing workspace, selection, version, and git info."""

    def __init__(self, parent=None, *, repo_root: Path | None = None) -> None:
        super().__init__(parent)
        self._repo_root = repo_root
        self._workspace = QLabel()
        self._project = QLabel()
        self._dataset = QLabel()
        self._version = QLabel(f"Version: {__version__}")
        self._git = QLabel()
        for widget in (self._workspace, self._project, self._dataset, self._version, self._git):
            self.addPermanentWidget(widget)

    def update_state(self, state: DesktopState) -> None:
        self._workspace.setText(f"Workspace: {state.workspace_name}")
        project_name = state.project_id or "(none)"
        dataset_name = state.dataset_id or "(none)"
        self._project.setText(f"Project: {project_name}")
        self._dataset.setText(f"Dataset: {dataset_name}")
        git_info = get_git_summary(self._repo_root)
        if git_info["available"] == "true":
            self._git.setText(
                f"Git: {git_info['branch']} {git_info['commit']} {git_info['tag']}"
            )
        else:
            self._git.setText("Git: unknown")
