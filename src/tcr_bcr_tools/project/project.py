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
        "pipeline": {},
        "outputs": {},
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
        """Update a pipeline step status (legacy status mapping)."""
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

    def get_pipeline_step(self, step_id: str) -> dict[str, Any]:
        """Return pipeline state for one step from project.yaml."""
        if not self._data:
            self.load()
        pipeline = self._data.get("pipeline", {})
        state = pipeline.get(step_id, {})
        if isinstance(state, dict):
            return dict(state)
        return {}

    def get_pipeline_status(self, step_id: str) -> str:
        """Return pipeline status for one step."""
        state = self.get_pipeline_step(step_id)
        return str(state.get("status", "pending"))

    def set_pipeline_step(
        self,
        step_id: str,
        status: str,
        *,
        finished: str | None = None,
        runtime: float | None = None,
        version: str | None = None,
    ) -> None:
        """Update pipeline state for one step in project.yaml."""
        if not self._data:
            self.load()
        pipeline = self._data.setdefault("pipeline", {})
        state = dict(pipeline.get(step_id, {}))
        state["status"] = status
        if finished is not None:
            state["finished"] = finished
        if runtime is not None:
            state["runtime"] = round(runtime, 3)
        if version is not None:
            state["version"] = version
        pipeline[step_id] = state
        legacy_status = self._data.setdefault("status", {})
        legacy_status[step_id] = status
        self.save()

    def reset_pipeline_step(self, step_id: str) -> None:
        """Clear pipeline state and outputs for one step."""
        if not self._data:
            self.load()
        pipeline = self._data.setdefault("pipeline", {})
        pipeline.pop(step_id, None)
        outputs = self._data.setdefault("outputs", {})
        outputs.pop(step_id, None)
        legacy_status = self._data.setdefault("status", {})
        legacy_status.pop(step_id, None)
        self.save()

    def get_step_outputs(self, step_id: str) -> dict[str, list[str]]:
        """Return registered outputs for one pipeline step."""
        if not self._data:
            self.load()
        outputs = self._data.get("outputs", {})
        step_outputs = outputs.get(step_id, {})
        if not isinstance(step_outputs, dict):
            return {}
        result: dict[str, list[str]] = {}
        for key, value in step_outputs.items():
            if isinstance(value, list):
                result[str(key)] = [str(item) for item in value]
        return result

    def set_step_outputs(self, step_id: str, outputs: dict[str, list[str]]) -> None:
        """Register outputs for one pipeline step."""
        if not self._data:
            self.load()
        registry = self._data.setdefault("outputs", {})
        registry[step_id] = {
            key: list(value) for key, value in outputs.items()
        }
        self.save()

    def get_output_registry(self) -> dict[str, dict[str, list[str]]]:
        """Return the full output registry from project.yaml."""
        if not self._data:
            self.load()
        outputs = self._data.get("outputs", {})
        if not isinstance(outputs, dict):
            return {}
        result: dict[str, dict[str, list[str]]] = {}
        for step_id, step_outputs in outputs.items():
            if isinstance(step_outputs, dict):
                result[str(step_id)] = self.get_step_outputs(str(step_id))
        return result

    def manifest(self) -> dict[str, Any]:
        """Return full project manifest data."""
        if not self._data:
            self.load()
        return self._data

    def list_output_files(self) -> list[str]:
        """List relative paths of files under outputs/."""
        if not self.outputs_dir.is_dir():
            return []
        return sorted(
            str(path.relative_to(self.outputs_dir))
            for path in self.outputs_dir.rglob("*")
            if path.is_file()
        )

    def list_figure_files(self) -> list[str]:
        """List relative paths of files under figures/."""
        if not self.figures_dir.is_dir():
            return []
        return sorted(
            str(path.relative_to(self.figures_dir))
            for path in self.figures_dir.rglob("*")
            if path.is_file()
        )

    def list_log_files(self) -> list[str]:
        """List relative paths of files under logs/."""
        if not self.logs_dir.is_dir():
            return []
        return sorted(
            str(path.relative_to(self.logs_dir))
            for path in self.logs_dir.rglob("*")
            if path.is_file()
        )

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
