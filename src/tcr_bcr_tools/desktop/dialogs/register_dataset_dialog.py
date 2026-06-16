"""Register dataset dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from tcr_bcr_tools.gui.constants import ADAPTER_OPTIONS


class RegisterDatasetDialog(QDialog):
    """Dialog for registering a shared dataset."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Register Dataset")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._dataset_id = QLineEdit()
        self._source = QLineEdit()
        self._adapter = QComboBox()
        self._adapter.addItems(ADAPTER_OPTIONS)
        self._raw_dir = QLineEdit()
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_raw)
        raw_row = QHBoxLayout()
        raw_row.addWidget(self._raw_dir)
        raw_row.addWidget(browse)
        form.addRow("Dataset ID:", self._dataset_id)
        form.addRow("Source:", self._source)
        form.addRow("Adapter:", self._adapter)
        form.addRow("Raw directory:", raw_row)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_raw(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Raw Directory", self._raw_dir.text())
        if path:
            self._raw_dir.setText(path)

    def dataset_id(self) -> str:
        return self._dataset_id.text().strip()

    def source(self) -> str:
        return self._source.text().strip()

    def adapter(self) -> str:
        return self._adapter.currentText()

    def raw_directory(self) -> str:
        return self._raw_dir.text().strip()
