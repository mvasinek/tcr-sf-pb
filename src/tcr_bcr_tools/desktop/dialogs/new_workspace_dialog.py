"""New workspace dialog."""

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

from tcr_bcr_tools.gui.constants import DEFAULT_WORKSPACE_NAME


class NewWorkspaceDialog(QDialog):
    """Dialog for creating a new workspace."""

    def __init__(self, parent=None, *, initial_location: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("New Workspace")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Workspace location:"))

        location_row = QHBoxLayout()
        self._location_edit = QLineEdit(initial_location)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_location)
        location_row.addWidget(self._location_edit)
        location_row.addWidget(browse)
        layout.addLayout(location_row)

        layout.addWidget(QLabel("Workspace name:"))
        self._name_edit = QLineEdit(DEFAULT_WORKSPACE_NAME)
        layout.addWidget(self._name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_location(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Parent Folder", self._location_edit.text())
        if path:
            self._location_edit.setText(path)

    def location(self) -> Path:
        return Path(self._location_edit.text().strip())

    def workspace_name(self) -> str:
        return self._name_edit.text().strip()
