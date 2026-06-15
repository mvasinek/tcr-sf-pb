"""Pipeline execution engine."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tcr_bcr_tools import __version__
from tcr_bcr_tools.git_info import get_git_summary
from tcr_bcr_tools.pipeline.history import (
    append_history_record,
    append_pipeline_log,
    load_history,
    save_history,
)
from tcr_bcr_tools.pipeline.registry import STEP_ORDER, get_registry, get_step
from tcr_bcr_tools.pipeline.step import (
    COMPLETED,
    FAILED,
    PENDING,
    RUNNING,
    SKIPPED,
    PipelineContext,
)
from tcr_bcr_tools.project.dataset import Dataset
from tcr_bcr_tools.project.project import Project
from tcr_bcr_tools.project.workspace import Workspace
from tcr_bcr_tools.validation.validator import ValidationGateError, report_allows_pipeline


class DependencyError(Exception):
    """Raised when pipeline step dependencies are not satisfied."""

    def __init__(self, step_id: str, missing: list[str]) -> None:
        self.step_id = step_id
        self.missing = missing
        super().__init__(
            f"Step '{step_id}' requires completed dependencies: {', '.join(missing)}"
        )


class PipelineRunner:
    """Execute registered pipeline steps for one project."""

    def __init__(
        self,
        workspace: Workspace,
        project: Project,
        *,
        force_recompute: bool = False,
        ignore_validation_errors: bool = False,
        repo_root: Path | None = None,
    ) -> None:
        self.workspace = workspace
        self.project = project
        self.force_recompute = force_recompute
        self.ignore_validation_errors = ignore_validation_errors
        self.repo_root = repo_root
        self.registry = get_registry()

    def _dataset(self) -> Dataset:
        datasets = self.project.manifest().get("datasets", [])
        if not datasets:
            raise ValueError("Project has no linked dataset.")
        return self.workspace.open_dataset(str(datasets[0]))

    def _context(self) -> PipelineContext:
        dataset = self._dataset()
        return PipelineContext(
            workspace=self.workspace,
            project=self.project,
            dataset=dataset,
            intermediate_dir=dataset.intermediate_dir,
            outputs_dir=self.project.outputs_dir,
            figures_dir=self.project.figures_dir,
            logs_dir=self.project.logs_dir,
            repo_root=self.repo_root,
        )

    def check_validation_gate(self, step_id: str) -> tuple[bool, str]:
        """Return whether dataset validation allows running a pipeline step."""
        if step_id == "validate_dataset":
            return True, ""
        report = self._dataset().load_validation_report()
        if report is None:
            return False, "Dataset has not been validated. Run validate_dataset first."
        return report_allows_pipeline(
            report,
            ignore_errors=self.ignore_validation_errors,
        )

    def load_history(self) -> list[dict[str, Any]]:
        """Load run history for the current project."""
        return load_history(self.project.logs_dir)

    def save_history(self, records: list[dict[str, Any]]) -> None:
        """Persist run history for the current project."""
        save_history(self.project.logs_dir, records)

    def validate_dependencies(self, step_id: str) -> tuple[bool, list[str]]:
        """Return whether dependencies are satisfied and any missing step ids."""
        step = get_step(step_id)
        missing: list[str] = []
        for dependency in step.dependencies:
            status = self.project.get_pipeline_status(dependency)
            if status != COMPLETED:
                missing.append(dependency)
        return len(missing) == 0, missing

    def needs_recompute(self, step_id: str) -> bool:
        """Return True when cached outputs are missing or force recompute is set."""
        if self.force_recompute:
            return True
        outputs = self.project.get_step_outputs(step_id)
        if not outputs:
            return True
        for paths in outputs.values():
            for rel_path in paths:
                if not (self.workspace.root / rel_path).exists():
                    return True
        return False

    def reset_step(self, step_id: str) -> None:
        """Clear pipeline state and outputs for one step."""
        get_step(step_id)
        self.project.reset_pipeline_step(step_id)

    def _log(self, step_id: str, level: str, message: str) -> None:
        append_pipeline_log(self.project.logs_dir, step_id, level, message)

    def _git_metadata(self) -> dict[str, str]:
        summary = get_git_summary(self.repo_root)
        return {
            "git_branch": summary.get("branch", "unknown"),
            "git_commit": summary.get("commit", "unknown"),
            "git_tag": summary.get("tag", "unknown"),
        }

    def _record_history(
        self,
        step_id: str,
        *,
        started: str,
        finished: str,
        duration: float,
        status: str,
        outputs: dict[str, list[str]],
    ) -> None:
        record = {
            "step": step_id,
            "started": started,
            "finished": finished,
            "duration": round(duration, 3),
            "status": status,
            "tool_version": __version__,
            "outputs": outputs,
            **self._git_metadata(),
        }
        append_history_record(self.project.logs_dir, record)

    def run_step(self, step_id: str) -> dict[str, Any]:
        """Run one pipeline step."""
        allowed, reason = self.check_validation_gate(step_id)
        if not allowed:
            self._log(step_id, "ERROR", reason)
            raise ValidationGateError(reason)

        step = get_step(step_id)
        ok, missing = self.validate_dependencies(step_id)
        if not ok:
            reason = (
                f"Missing completed dependencies: {', '.join(missing)}"
            )
            self._log(step_id, "ERROR", reason)
            raise DependencyError(step_id, missing)

        current_status = self.project.get_pipeline_status(step_id)
        if current_status == COMPLETED and not self.needs_recompute(step_id):
            self._log(step_id, "INFO", "Reusing existing output")
            self.project.set_pipeline_step(step_id, SKIPPED)
            self._record_history(
                step_id,
                started=datetime.now().isoformat(timespec="seconds"),
                finished=datetime.now().isoformat(timespec="seconds"),
                duration=0.0,
                status=SKIPPED,
                outputs=self.project.get_step_outputs(step_id),
            )
            return {
                "step_id": step_id,
                "status": SKIPPED,
                "outputs": self.project.get_step_outputs(step_id),
                "message": "Reused existing output",
            }

        started_at = datetime.now().isoformat(timespec="seconds")
        self.project.set_pipeline_step(step_id, RUNNING)
        self._log(step_id, "INFO", "Starting step")
        start_time = time.perf_counter()

        try:
            ctx = self._context()
            outputs = step.callable(ctx)
            duration = time.perf_counter() - start_time
            finished_at = datetime.now().isoformat(timespec="seconds")
            self.project.set_pipeline_step(
                step_id,
                COMPLETED,
                finished=finished_at,
                runtime=duration,
                version=step.version,
            )
            self.project.set_step_outputs(step_id, outputs)
            self._record_history(
                step_id,
                started=started_at,
                finished=finished_at,
                duration=duration,
                status=COMPLETED,
                outputs=outputs,
            )
            self._log(step_id, "INFO", f"Completed in {duration:.2f}s")
            return {
                "step_id": step_id,
                "status": COMPLETED,
                "outputs": outputs,
                "duration": duration,
                "message": "Completed",
            }
        except Exception as exc:  # noqa: BLE001 - pipeline must record failures
            duration = time.perf_counter() - start_time
            finished_at = datetime.now().isoformat(timespec="seconds")
            self.project.set_pipeline_step(
                step_id,
                FAILED,
                finished=finished_at,
                runtime=duration,
                version=step.version,
            )
            self._record_history(
                step_id,
                started=started_at,
                finished=finished_at,
                duration=duration,
                status=FAILED,
                outputs={},
            )
            self._log(step_id, "ERROR", str(exc))
            return {
                "step_id": step_id,
                "status": FAILED,
                "outputs": {},
                "duration": duration,
                "message": str(exc),
            }

    def run(self) -> list[dict[str, Any]]:
        """Run all pipeline steps in order."""
        results: list[dict[str, Any]] = []
        for step_id in STEP_ORDER:
            if step_id not in self.registry:
                continue
            status = self.project.get_pipeline_status(step_id)
            if status == COMPLETED and not self.needs_recompute(step_id):
                results.append(
                    {
                        "step_id": step_id,
                        "status": SKIPPED,
                        "message": "Reused existing output",
                    }
                )
                continue
            result = self.run_step(step_id)
            results.append(result)
            if result["status"] == FAILED:
                break
        return results

    def resume(self) -> list[dict[str, Any]]:
        """Resume pipeline execution from the first incomplete step."""
        start_index = 0
        for index, step_id in enumerate(STEP_ORDER):
            if self.project.get_pipeline_status(step_id) != COMPLETED:
                start_index = index
                break
        else:
            return []

        results: list[dict[str, Any]] = []
        for step_id in STEP_ORDER[start_index:]:
            if step_id not in self.registry:
                continue
            status = self.project.get_pipeline_status(step_id)
            if status == COMPLETED and not self.needs_recompute(step_id):
                results.append(
                    {
                        "step_id": step_id,
                        "status": SKIPPED,
                        "message": "Reused existing output",
                    }
                )
                continue
            result = self.run_step(step_id)
            results.append(result)
            if result["status"] == FAILED:
                break
        return results

    def step_states(self) -> list[dict[str, Any]]:
        """Return registry metadata merged with project pipeline state."""
        states: list[dict[str, Any]] = []
        for step_id in STEP_ORDER:
            if step_id not in self.registry:
                continue
            step = self.registry[step_id]
            pipeline_state = self.project.get_pipeline_step(step_id)
            states.append(
                {
                    "id": step.id,
                    "name": step.name,
                    "description": step.description,
                    "version": step.version,
                    "dependencies": list(step.dependencies),
                    "output_directory": step.output_directory,
                    "status": pipeline_state.get("status", PENDING),
                    "finished": pipeline_state.get("finished", ""),
                    "runtime": pipeline_state.get("runtime"),
                    "outputs": self.project.get_step_outputs(step_id),
                }
            )
        return states
