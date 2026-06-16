"""Pipeline steps table (read-only in 0.6.0)."""

from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class PipelinePanel(QWidget):
    """List pipeline steps and statuses."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("Pipeline")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Step", "Status", "Dependencies"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

    def show_steps(self, rows: list[dict[str, str]]) -> None:
        self._table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self._table.setItem(row_index, 0, QTableWidgetItem(row.get("step", "")))
            self._table.setItem(row_index, 1, QTableWidgetItem(row.get("status", "")))
            self._table.setItem(row_index, 2, QTableWidgetItem(row.get("dependencies", "")))
