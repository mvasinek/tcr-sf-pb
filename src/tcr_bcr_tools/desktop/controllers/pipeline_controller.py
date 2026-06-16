"""Pipeline panel controller (placeholder for 0.6.2 integration)."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from tcr_bcr_tools.desktop.state import DesktopState
from tcr_bcr_tools.pipeline.registry import STEP_ORDER, get_step


class PipelineController(QObject):
    """Expose pipeline step metadata for the desktop UI."""

    message = Signal(str)

    def __init__(self, state: DesktopState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = state

    def list_steps(self) -> list[dict[str, str]]:
        project = self._state.project
        rows: list[dict[str, str]] = []
        for step_id in STEP_ORDER:
            try:
                step = get_step(step_id)
            except KeyError:
                continue
            status = ""
            if project is not None:
                status = project.get_pipeline_status(step_id)
            rows.append(
                {
                    "step": step.name or step_id,
                    "status": status or "pending",
                    "dependencies": ", ".join(step.dependencies or []) or "(none)",
                }
            )
        return rows

    def run_selected_step(self) -> None:
        self.message.emit("Pipeline execution will be integrated in a later desktop release.")

    def run_all(self) -> None:
        self.message.emit("Run all pipeline steps — coming in a later desktop release.")

    def stop(self) -> None:
        self.message.emit("Stop pipeline — coming in a later desktop release.")
