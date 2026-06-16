"""Application state shared across desktop controllers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tcr_bcr_tools.project import Dataset, Project, Workspace


@dataclass
class DesktopState:
    """Mutable application state for the desktop shell."""

    workspace: Workspace | None = None
    project: Project | None = None
    dataset: Dataset | None = None
    project_id: str = ""
    dataset_id: str = ""
    selection_kind: str = ""  # workspace | project | dataset | none

    def clear_workspace(self) -> None:
        self.workspace = None
        self.project = None
        self.dataset = None
        self.project_id = ""
        self.dataset_id = ""
        self.selection_kind = "none"

    def set_workspace(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.project = None
        self.dataset = None
        self.project_id = ""
        self.dataset_id = ""
        self.selection_kind = "workspace"

    def set_project(self, project: Project) -> None:
        self.project = project
        self.dataset = None
        self.project_id = project.project_id
        self.dataset_id = ""
        self.selection_kind = "project"

    def set_dataset(self, dataset: Dataset) -> None:
        self.dataset = dataset
        self.project = None
        self.project_id = ""
        self.dataset_id = dataset.dataset_id
        self.selection_kind = "dataset"

    @property
    def workspace_name(self) -> str:
        if self.workspace is None:
            return "(none)"
        from tcr_bcr_tools.project.recent_workspaces import get_workspace_display_name

        return get_workspace_display_name(self.workspace.root)

    @property
    def workspace_path(self) -> Path | None:
        return self.workspace.root if self.workspace else None
