"""Dataset selection controller."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from tcr_bcr_tools.desktop.state import DesktopState
from tcr_bcr_tools.gui.dialogs import register_dataset_from_dialog
from tcr_bcr_tools.project import Dataset, Workspace


class DatasetController(QObject):
    """Manage dataset selection and registration."""

    dataset_selected = Signal(object)
    message = Signal(str)
    error = Signal(str)

    def __init__(self, state: DesktopState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = state

    def select_dataset(self, dataset_id: str) -> bool:
        workspace = self._state.workspace
        if workspace is None:
            self.error.emit("Open a workspace first.")
            return False
        try:
            dataset = workspace.open_dataset(dataset_id)
        except FileNotFoundError as exc:
            self.error.emit(str(exc))
            return False
        self._state.set_dataset(dataset)
        self.message.emit(f"Dataset selected: {dataset_id}")
        self.dataset_selected.emit(dataset)
        return True

    def register_dataset(
        self,
        workspace: Workspace,
        *,
        dataset_id: str,
        source: str,
        adapter: str,
        raw_directory: str,
    ) -> Dataset | None:
        if not dataset_id.strip():
            self.error.emit("Dataset ID is required.")
            return None
        dataset = register_dataset_from_dialog(
            workspace,
            dataset_id=dataset_id.strip(),
            source=source.strip(),
            adapter=adapter,
            raw_directory=raw_directory.strip(),
        )
        self._state.set_dataset(dataset)
        self.message.emit(f"Dataset registered: {dataset.dataset_id}")
        self.dataset_selected.emit(dataset)
        return dataset
