"""Project selection controller."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from tcr_bcr_tools.desktop.state import DesktopState
from tcr_bcr_tools.gui.dialogs import create_project_from_dialog
from tcr_bcr_tools.project import Project, Workspace


class ProjectController(QObject):
    """Manage project selection and creation."""

    project_selected = Signal(object)
    message = Signal(str)
    error = Signal(str)

    def __init__(self, state: DesktopState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = state

    def select_project(self, project_id: str) -> bool:
        workspace = self._state.workspace
        if workspace is None:
            self.error.emit("Open a workspace first.")
            return False
        try:
            project = workspace.open_project(project_id)
        except FileNotFoundError as exc:
            self.error.emit(str(exc))
            return False
        self._state.set_project(project)
        self.message.emit(f"Project selected: {project_id}")
        self.project_selected.emit(project)
        return True

    def create_project(
        self,
        workspace: Workspace,
        *,
        name: str,
        description: str,
        dataset_id: str,
        adapter: str,
    ) -> Project | None:
        if not name.strip():
            self.error.emit("Project name is required.")
            return None
        project = create_project_from_dialog(
            workspace,
            name=name.strip(),
            description=description.strip(),
            dataset_id=dataset_id,
            adapter=adapter,
        )
        self._state.set_project(project)
        self.message.emit(f"Project created: {project.project_id}")
        self.project_selected.emit(project)
        return project
