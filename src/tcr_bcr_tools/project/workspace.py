"""Workspace layout, settings, and project/dataset management."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from tcr_bcr_tools import __version__
from tcr_bcr_tools.project.dataset import DATASET_MANIFEST, Dataset
from tcr_bcr_tools.project.manifest import load_yaml, save_yaml
from tcr_bcr_tools.project.project import PROJECT_MANIFEST, Project

SETTINGS_MANIFEST = "settings.yaml"


def _default_settings() -> dict[str, Any]:
    return {
        "workspace": {
            "version": __version__,
        },
        "default_project": "",
        "default_dataset": "",
    }


class Workspace:
    """Top-level workspace containing shared datasets and analysis projects."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.settings_path = root / SETTINGS_MANIFEST
        self.datasets_dir = root / "datasets"
        self.projects_dir = root / "projects"
        self.cache_dir = root / "cache"
        self.logs_dir = root / "logs"
        self._settings: dict[str, Any] = {}

    @property
    def settings(self) -> dict[str, Any]:
        """Return loaded workspace settings."""
        if not self._settings:
            self.load()
        return self._settings

    def load(self) -> dict[str, Any]:
        """Load workspace settings; create default layout if missing."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.datasets_dir.mkdir(exist_ok=True)
        self.projects_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        if self.settings_path.exists():
            self._settings = load_yaml(self.settings_path)
        else:
            self._settings = _default_settings()
            self.save()
        return self._settings

    def save(self) -> None:
        """Persist workspace settings."""
        self.root.mkdir(parents=True, exist_ok=True)
        save_yaml(self.settings_path, self._settings)

    def list_projects(self) -> list[str]:
        """List project ids with a valid project.yaml."""
        if not self.projects_dir.is_dir():
            return []
        return sorted(
            item.name
            for item in self.projects_dir.iterdir()
            if item.is_dir() and (item / PROJECT_MANIFEST).exists()
        )

    def list_datasets(self) -> list[str]:
        """List dataset ids with a valid dataset.yaml."""
        if not self.datasets_dir.is_dir():
            return []
        return sorted(
            item.name
            for item in self.datasets_dir.iterdir()
            if item.is_dir() and (item / DATASET_MANIFEST).exists()
        )

    def create_project(
        self,
        project_id: str,
        *,
        name: str = "",
        description: str = "",
        datasets: list[str] | None = None,
        adapter: str = "tenx",
        analysis: str = "",
        status: dict[str, str] | None = None,
    ) -> Project:
        """Create a new analysis project."""
        if not self._settings:
            self.load()
        project = Project.create(
            self.projects_dir,
            project_id,
            name=name,
            description=description,
            datasets=datasets,
            adapter=adapter,
            analysis=analysis,
            status=status,
        )
        if not self._settings.get("default_project"):
            self._settings["default_project"] = project_id
            self.save()
        return project

    def create_dataset(
        self,
        dataset_id: str,
        *,
        title: str = "",
        source: str = "",
        adapter: str = "tenx",
        raw_directory: Path | str | None = None,
    ) -> Dataset:
        """Create a new shared dataset."""
        if not self._settings:
            self.load()
        raw_source = ""
        if raw_directory:
            raw_source = str(Path(raw_directory).expanduser().resolve())
        dataset = Dataset.create(
            self.datasets_dir,
            dataset_id,
            title=title or dataset_id,
            source=source,
            adapter=adapter,
            raw_source=raw_source,
        )
        if not self._settings.get("default_dataset"):
            self._settings["default_dataset"] = dataset_id
            self.save()
        return dataset

    def register_dataset(
        self,
        dataset_id: str,
        *,
        source: str = "",
        adapter: str = "tenx",
        raw_directory: Path | str | None = None,
    ) -> Dataset:
        """Register a dataset with optional external raw directory."""
        return self.create_dataset(
            dataset_id,
            source=source,
            adapter=adapter,
            raw_directory=raw_directory,
        )

    def delete_project(self, project_id: str) -> None:
        """Delete a project directory and manifest."""
        if not self._settings:
            self.load()
        project_root = self.projects_dir / project_id
        if project_root.exists():
            shutil.rmtree(project_root)
        if self._settings.get("default_project") == project_id:
            self._settings["default_project"] = ""
            self.save()

    @staticmethod
    def slugify_project_id(name: str) -> str:
        """Convert a display name to a filesystem-safe project id."""
        slug = re.sub(r"[^\w\s-]", "", name.strip())
        slug = re.sub(r"[\s-]+", "_", slug)
        return slug or "project"

    def open_project(self, project_id: str) -> Project:
        """Open an existing project by id."""
        project_root = self.projects_dir / project_id
        if not (project_root / PROJECT_MANIFEST).exists():
            raise FileNotFoundError(f"Project not found: {project_id}")
        project = Project(project_root, project_id)
        project.load()
        return project

    def open_dataset(self, dataset_id: str) -> Dataset:
        """Open an existing dataset by id."""
        dataset_root = self.datasets_dir / dataset_id
        if not (dataset_root / DATASET_MANIFEST).exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_id}")
        dataset = Dataset(dataset_root, dataset_id)
        dataset.load()
        return dataset
