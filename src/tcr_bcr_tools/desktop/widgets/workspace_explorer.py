"""Workspace explorer tree widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from tcr_bcr_tools.project import Workspace


class WorkspaceExplorer(QWidget):
    """Tree view of workspace projects and datasets."""

    project_selected = Signal(str)
    dataset_selected = Signal(str)
    workspace_selected = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree)

    def refresh(self, workspace: Workspace | None) -> None:
        self._tree.clear()
        if workspace is None:
            root = QTreeWidgetItem(["(no workspace)"])
            self._tree.addTopLevelItem(root)
            return

        display_name = workspace.root.name
        root = QTreeWidgetItem([display_name])
        root.setData(0, 256, ("workspace", ""))
        self._tree.addTopLevelItem(root)

        projects_node = QTreeWidgetItem(["Projects"])
        projects_node.setData(0, 256, ("group", "projects"))
        for project_id in workspace.list_projects():
            item = QTreeWidgetItem([project_id])
            item.setData(0, 256, ("project", project_id))
            projects_node.addChild(item)
        root.addChild(projects_node)

        datasets_node = QTreeWidgetItem(["Datasets"])
        datasets_node.setData(0, 256, ("group", "datasets"))
        for dataset_id in workspace.list_datasets():
            item = QTreeWidgetItem([dataset_id])
            item.setData(0, 256, ("dataset", dataset_id))
            datasets_node.addChild(item)
        root.addChild(datasets_node)
        root.setExpanded(True)
        projects_node.setExpanded(True)
        datasets_node.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, 256)
        if not data:
            return
        kind, value = data
        if kind == "workspace":
            self.workspace_selected.emit()
        elif kind == "project":
            self.project_selected.emit(value)
        elif kind == "dataset":
            self.dataset_selected.emit(value)
