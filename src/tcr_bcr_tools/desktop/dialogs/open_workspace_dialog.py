"""Open workspace dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class OpenWorkspaceDialog(QDialog):
    """Dialog for selecting an existing workspace folder."""

    def __init__(self, parent=None, *, initial_path: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Open Workspace")
        self._selected_path = ""

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Workspace folder:"))

        row = QHBoxLayout()
        self._path_edit = QLineEdit(initial_path)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row.addWidget(self._path_edit)
        row.addWidget(browse)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Workspace Folder", self._path_edit.text())
        if path:
            self._path_edit.setText(path)

    def workspace_path(self) -> Path:
        return Path(self._path_edit.text().strip())
