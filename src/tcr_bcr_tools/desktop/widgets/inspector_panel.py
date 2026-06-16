"""Inspector panel for the current selection."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from tcr_bcr_tools.desktop.state import DesktopState


class InspectorPanel(QWidget):
    """Show details for the currently selected item."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("Inspector")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        self._form = QFormLayout()
        self._type = QLabel("-")
        self._name = QLabel("-")
        self._path = QLabel("-")
        self._created = QLabel("-")
        self._modified = QLabel("-")
        self._form.addRow("Type:", self._type)
        self._form.addRow("Name:", self._name)
        self._form.addRow("Path:", self._path)
        self._form.addRow("Created:", self._created)
        self._form.addRow("Modified:", self._modified)
        layout.addLayout(self._form)
        layout.addStretch()

    def update_state(self, state: DesktopState) -> None:
        if state.selection_kind == "project" and state.project is not None:
            data = state.project.load()
            meta = data.get("project", {})
            self._type.setText("Project")
            self._name.setText(str(meta.get("name", state.project_id)))
            self._path.setText(str(state.project.root))
            self._created.setText(str(meta.get("created", "")))
            self._modified.setText(str(meta.get("modified", "")))
        elif state.selection_kind == "dataset" and state.dataset is not None:
            data = state.dataset.load()
            meta = data.get("dataset", {})
            self._type.setText("Dataset")
            self._name.setText(str(meta.get("title", state.dataset_id)))
            self._path.setText(str(state.dataset.root))
            self._created.setText(str(meta.get("created", "")))
            self._modified.setText("-")
        elif state.workspace is not None:
            self._type.setText("Workspace")
            self._name.setText(state.workspace_name)
            self._path.setText(str(state.workspace.root))
            self._created.setText("-")
            self._modified.setText("-")
        else:
            self._type.setText("-")
            self._name.setText("-")
            self._path.setText("-")
            self._created.setText("-")
            self._modified.setText("-")
