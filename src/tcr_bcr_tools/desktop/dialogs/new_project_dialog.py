"""New project dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from tcr_bcr_tools.gui.constants import ADAPTER_OPTIONS


class NewProjectDialog(QDialog):
    """Dialog for creating a new analysis project."""

    def __init__(self, parent=None, *, datasets: list[str] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit()
        self._description = QLineEdit()
        self._dataset = QComboBox()
        self._dataset.addItem("(none)", "")
        for dataset_id in datasets or []:
            self._dataset.addItem(dataset_id, dataset_id)
        self._adapter = QComboBox()
        self._adapter.addItems(ADAPTER_OPTIONS)
        form.addRow("Project name:", self._name)
        form.addRow("Description:", self._description)
        form.addRow("Dataset:", self._dataset)
        form.addRow("Adapter:", self._adapter)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def project_name(self) -> str:
        return self._name.text().strip()

    def description(self) -> str:
        return self._description.text().strip()

    def dataset_id(self) -> str:
        return str(self._dataset.currentData() or "")

    def adapter(self) -> str:
        return self._adapter.currentText()
