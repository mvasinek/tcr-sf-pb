"""Read-only dataset overview panel."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from tcr_bcr_tools.adapters.schema import UNIFIED_ANNOTATIONS_FILE
from tcr_bcr_tools.project import Dataset


class DatasetOverview(QWidget):
    """Display dataset metadata and validation status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("Dataset Overview")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        self._form = QFormLayout()
        self._dataset_id = QLabel("-")
        self._source = QLabel("-")
        self._adapter = QLabel("-")
        self._raw_dir = QLabel("-")
        self._intermediate = QLabel("-")
        self._validation = QLabel("-")
        self._unified = QLabel("-")
        self._form.addRow("Dataset ID:", self._dataset_id)
        self._form.addRow("Source:", self._source)
        self._form.addRow("Adapter:", self._adapter)
        self._form.addRow("Raw directory:", self._raw_dir)
        self._form.addRow("Intermediate directory:", self._intermediate)
        self._form.addRow("Validation status:", self._validation)
        self._form.addRow("Unified output status:", self._unified)
        layout.addLayout(self._form)
        layout.addStretch()

    def show_dataset(self, dataset: Dataset | None) -> None:
        if dataset is None:
            for label in (
                self._dataset_id,
                self._source,
                self._adapter,
                self._raw_dir,
                self._intermediate,
                self._validation,
                self._unified,
            ):
                label.setText("-")
            return
        data = dataset.load()
        meta = data.get("dataset", {})
        self._dataset_id.setText(str(meta.get("id", dataset.dataset_id)))
        self._source.setText(str(meta.get("source", "")))
        self._adapter.setText(str(meta.get("adapter", "")))
        raw_source = dataset.raw_source_path()
        self._raw_dir.setText(str(raw_source or dataset.raw_dir))
        self._intermediate.setText(str(dataset.intermediate_dir))
        summary_path = dataset.intermediate_dir / "validation_summary.json"
        self._validation.setText("available" if summary_path.exists() else "not run")
        unified = dataset.intermediate_dir / UNIFIED_ANNOTATIONS_FILE
        self._unified.setText("available" if unified.exists() else "not built")
