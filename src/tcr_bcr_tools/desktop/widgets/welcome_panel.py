"""Welcome panel shown when no workspace is open."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class WelcomePanel(QWidget):
    """Landing screen with workspace actions."""

    new_workspace_requested = Signal()
    open_workspace_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("TCR SF/PB Analysis")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Create or open a workspace to begin."))
        new_btn = QPushButton("New Workspace")
        open_btn = QPushButton("Open Workspace")
        new_btn.clicked.connect(self.new_workspace_requested.emit)
        open_btn.clicked.connect(self.open_workspace_requested.emit)
        layout.addWidget(new_btn)
        layout.addWidget(open_btn)
        layout.addStretch()
