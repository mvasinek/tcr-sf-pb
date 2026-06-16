"""Workspace controller — create/open workspace without UI dependencies."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from tcr_bcr_tools.desktop.state import DesktopState
from tcr_bcr_tools.desktop import settings as app_settings
from tcr_bcr_tools.project import Workspace
from tcr_bcr_tools.project.recent_workspaces import add_recent_workspace, load_recent_workspaces
from tcr_bcr_tools.project.workspace import SETTINGS_MANIFEST


def validate_workspace(path: Path) -> tuple[bool, str]:
    """Return whether *path* is an existing workspace root."""
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return False, "Workspace folder does not exist."
    if not (root / SETTINGS_MANIFEST).exists():
        return False, "Not a valid workspace (missing settings.yaml)."
    return True, ""


class WorkspaceController(QObject):
    """Manage workspace lifecycle for the desktop application."""

    workspace_opened = Signal(object)
    workspace_closed = Signal()
    message = Signal(str)
    error = Signal(str)

    def __init__(self, state: DesktopState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = state

    @property
    def state(self) -> DesktopState:
        return self._state

    def recent_workspaces(self) -> list[dict]:
        return load_recent_workspaces()

    def open_workspace(self, path: Path) -> bool:
        valid, err = validate_workspace(path)
        if not valid:
            self.error.emit(err)
            return False
        workspace = Workspace(Path(path).expanduser().resolve())
        workspace.load()
        self._state.set_workspace(workspace)
        add_recent_workspace(workspace.root)
        app_settings.set_last_workspace(str(workspace.root))
        self.message.emit(f"Workspace opened: {workspace.root.name}")
        self.workspace_opened.emit(workspace)
        return True

    def create_workspace(self, location: Path, name: str) -> bool:
        folder_name = name.strip()
        if not folder_name:
            self.error.emit("Workspace name is required.")
            return False
        root = Path(location).expanduser().resolve() / folder_name
        if root.exists() and (root / SETTINGS_MANIFEST).exists():
            self.error.emit("A workspace already exists at this location.")
            return False
        workspace = Workspace(root)
        workspace.load()
        self._state.set_workspace(workspace)
        add_recent_workspace(workspace.root)
        app_settings.set_last_workspace(str(workspace.root))
        self.message.emit(f"Workspace created: {workspace.root.name}")
        self.workspace_opened.emit(workspace)
        return True

    def close_workspace(self) -> None:
        self._state.clear_workspace()
        self.workspace_closed.emit()
        self.message.emit("Workspace closed.")
