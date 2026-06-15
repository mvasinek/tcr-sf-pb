"""Pipeline step definition and execution context."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from tcr_bcr_tools.project.dataset import Dataset
from tcr_bcr_tools.project.project import Project
from tcr_bcr_tools.project.workspace import Workspace

StepCallable = Callable[["PipelineContext"], dict[str, list[str]]]

PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
SKIPPED = "skipped"

STEP_STATUSES = (PENDING, RUNNING, COMPLETED, FAILED, SKIPPED)


@dataclass
class PipelineContext:
    """Runtime paths and handles passed to each pipeline step."""

    workspace: Workspace
    project: Project
    dataset: Dataset
    intermediate_dir: Path
    outputs_dir: Path
    figures_dir: Path
    logs_dir: Path
    repo_root: Path | None = None

    def raw_input_dir(self) -> Path:
        """Return external raw source or dataset raw directory."""
        source = self.dataset.raw_source_path()
        if source and source.exists():
            return source
        return self.dataset.raw_dir


@dataclass
class PipelineStep:
    """One registered analytical step in the pipeline."""

    id: str
    name: str
    description: str
    version: str
    dependencies: list[str]
    callable: StepCallable
    output_directory: str
    status: str = PENDING
    outputs: dict[str, list[str]] = field(default_factory=dict)
    runtime: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize step metadata for display."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "dependencies": list(self.dependencies),
            "output_directory": self.output_directory,
            "status": self.status,
            "outputs": dict(self.outputs),
            "runtime": self.runtime,
        }
