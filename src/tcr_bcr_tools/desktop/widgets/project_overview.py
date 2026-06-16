"""Read-only project overview panel."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from tcr_bcr_tools.project import Project


class ProjectOverview(QWidget):
    """Display project metadata and pipeline summary."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("Project Overview")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        self._form = QFormLayout()
        self._name = QLabel("-")
        self._description = QLabel("-")
        self._datasets = QLabel("-")
        self._adapter = QLabel("-")
        self._pipeline = QLabel("-")
        self._outputs = QLabel("-")
        self._form.addRow("Project name:", self._name)
        self._form.addRow("Description:", self._description)
        self._form.addRow("Datasets:", self._datasets)
        self._form.addRow("Adapter:", self._adapter)
        self._form.addRow("Pipeline status:", self._pipeline)
        self._form.addRow("Outputs summary:", self._outputs)
        layout.addLayout(self._form)
        layout.addStretch()

    def show_project(self, project: Project | None) -> None:
        if project is None:
            self._name.setText("-")
            self._description.setText("-")
            self._datasets.setText("-")
            self._adapter.setText("-")
            self._pipeline.setText("-")
            self._outputs.setText("-")
            return
        data = project.load()
        project_meta = data.get("project", {})
        self._name.setText(str(project_meta.get("name", project.project_id)))
        self._description.setText(str(project_meta.get("description", "")))
        self._datasets.setText(", ".join(data.get("datasets", [])) or "(none)")
        self._adapter.setText(str(data.get("adapter", "")))
        status = project.get_status()
        if isinstance(status, dict) and status:
            parts = [f"{key}: {value}" for key, value in status.items()]
            self._pipeline.setText("; ".join(parts))
        else:
            self._pipeline.setText("(no status)")
        outputs = project.list_output_files()
        self._outputs.setText(str(len(outputs)) + " file(s)" if outputs else "(none)")
