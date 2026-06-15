"""Form actions for creating projects and registering datasets."""

from __future__ import annotations

from pathlib import Path

from tcr_bcr_tools.project import Dataset, Project, Workspace
from tcr_bcr_tools.project.workspace import Workspace as WorkspaceClass


def create_project_from_dialog(
    workspace: Workspace,
    *,
    name: str,
    description: str,
    dataset_id: str,
    adapter: str,
) -> Project:
    """Create a project using workspace API."""
    project_id = WorkspaceClass.slugify_project_id(name)
    datasets = [dataset_id] if dataset_id else []
    return workspace.create_project(
        project_id,
        name=name,
        description=description,
        datasets=datasets,
        adapter=adapter,
    )


def register_dataset_from_dialog(
    workspace: Workspace,
    *,
    dataset_id: str,
    source: str,
    adapter: str,
    raw_directory: str,
) -> Dataset:
    """Register a dataset using workspace API."""
    raw_path = Path(raw_directory).expanduser() if raw_directory else None
    return workspace.register_dataset(
        dataset_id,
        source=source,
        adapter=adapter,
        raw_directory=raw_path,
    )
