"""Results panel placeholder."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ResultsPanel(QWidget):
    """Placeholder until desktop results browser is implemented."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("Results")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Results browser will be implemented in a later desktop release."))
        layout.addStretch()
