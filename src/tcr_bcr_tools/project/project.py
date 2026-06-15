"""Project manifest and artifact directories."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from tcr_bcr_tools import __version__
from tcr_bcr_tools.project.manifest import load_yaml, save_yaml

PROJECT_MANIFEST = "project.yaml"


def _default_project_manifest(
    project_id: str,
    *,
    name: str = "",
    description: str = "",
    datasets: list[str] | None = None,
    adapter: str = "tenx",
    analysis: str = "",
) -> dict[str, Any]:
    today = date.today().isoformat()
    return {
        "project": {
            "name": name or project_id,
            "description": description,
            "created": today,
            "modified": today,
        },
        "tool": {
            "version": __version__,
        },
        "datasets": datasets or [],
        "adapter": adapter,
        "analysis": analysis,
        "status": {},
    }


class Project:
    """One analysis project referencing shared datasets."""

    def __init__(self, root: Path, project_id: str) -> None:
        self.root = root
        self.project_id = project_id
        self.manifest_path = root / PROJECT_MANIFEST
        self._data: dict[str, Any] = {}

    @property
    def outputs_dir(self) -> Path:
        return self.root / "outputs"

    @property
    def figures_dir(self) -> Path:
        return self.root / "figures"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    def load(self) -> dict[str, Any]:
        """Load project manifest from disk."""
        self._data = load_yaml(self.manifest_path)
        return self._data

    def save(self) -> None:
        """Persist project manifest to disk."""
        project_meta = self._data.setdefault("project", {})
        project_meta["modified"] = date.today().isoformat()
        save_yaml(self.manifest_path, self._data)

    def set_status(self, step: str, value: str) -> None:
        """Update a pipeline step status."""
        if not self._data:
            self.load()
        status = self._data.setdefault("status", {})
        status[step] = value
        self.save()

    def get_status(self, step: str | None = None) -> str | dict[str, str]:
        """Return one step status or the full status mapping."""
        if not self._data:
            self.load()
        status = self._data.get("status", {})
        if step is None:
            return dict(status)
        return str(status.get(step, ""))

    def add_output(self, relative_path: str, content: str = "") -> Path:
        """Create or register a file under outputs/."""
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        target = self.outputs_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if content:
            target.write_text(content, encoding="utf-8")
        return target

    def add_figure(self, relative_path: str, content: bytes = b"") -> Path:
        """Create or register a file under figures/."""
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        target = self.figures_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if content:
            target.write_bytes(content)
        return target

    def add_log(self, relative_path: str, content: str = "") -> Path:
        """Create or register a file under logs/."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        target = self.logs_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if content:
            target.write_text(content, encoding="utf-8")
        return target

    @classmethod
    def create(
        cls,
        projects_root: Path,
        project_id: str,
        *,
        name: str = "",
        description: str = "",
        datasets: list[str] | None = None,
        adapter: str = "tenx",
        analysis: str = "",
        status: dict[str, str] | None = None,
    ) -> Project:
        """Create a new project directory and manifest."""
        root = projects_root / project_id
        root.mkdir(parents=True, exist_ok=True)
        for subdir in ("outputs", "figures", "logs", "cache"):
            (root / subdir).mkdir(exist_ok=True)

        instance = cls(root, project_id)
        instance._data = _default_project_manifest(
            project_id,
            name=name,
            description=description,
            datasets=datasets,
            adapter=adapter,
            analysis=analysis,
        )
        if status:
            instance._data["status"] = status
        instance.save()
        return instance
