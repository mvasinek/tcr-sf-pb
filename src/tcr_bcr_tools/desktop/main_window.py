"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolBar,
)

from tcr_bcr_tools import __version__
from tcr_bcr_tools.desktop import settings as app_settings
from tcr_bcr_tools.desktop.actions import (
    build_dataset_actions,
    build_file_actions,
    build_help_actions,
    build_pipeline_actions,
    build_project_actions,
    build_toolbar_actions,
    build_view_actions,
)
from tcr_bcr_tools.desktop.controllers import (
    DatasetController,
    PipelineController,
    ProjectController,
    WorkspaceController,
)
from tcr_bcr_tools.desktop.dialogs import (
    NewProjectDialog,
    NewWorkspaceDialog,
    RegisterDatasetDialog,
)
from tcr_bcr_tools.desktop.resources import APP_TITLE
from tcr_bcr_tools.desktop.state import DesktopState
from tcr_bcr_tools.desktop.widgets import (
    AppStatusBar,
    DatasetOverview,
    InspectorPanel,
    LogViewer,
    PipelinePanel,
    ProjectOverview,
    ResultsPanel,
    WelcomePanel,
    WorkspaceExplorer,
)


class MainWindow(QMainWindow):
    """Primary desktop shell with menu, toolbar, docks, and central panels."""

    def __init__(self, repo_root: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self._repo_root = repo_root
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 800)

        self._state = DesktopState()
        self._workspace_controller = WorkspaceController(self._state, self)
        self._project_controller = ProjectController(self._state, self)
        self._dataset_controller = DatasetController(self._state, self)
        self._pipeline_controller = PipelineController(self._state, self)

        self._recent_menu = None
        self._build_ui()
        self._connect_signals()
        app_settings.restore_window_geometry(self)
        self._log("Application started.")
        self._refresh_ui()

    def _build_ui(self) -> None:
        self._welcome = WelcomePanel()
        self._project_overview = ProjectOverview()
        self._dataset_overview = DatasetOverview()
        self._pipeline_panel = PipelinePanel()
        self._results_panel = ResultsPanel()

        self._stack = QStackedWidget()
        self._stack.addWidget(self._welcome)
        self._stack.addWidget(self._project_overview)
        self._stack.addWidget(self._dataset_overview)
        self._stack.addWidget(self._pipeline_panel)
        self._stack.addWidget(self._results_panel)
        self.setCentralWidget(self._stack)

        self._explorer = WorkspaceExplorer()
        explorer_dock = QDockWidget("Workspace Explorer", self)
        explorer_dock.setObjectName("WorkspaceExplorerDock")
        explorer_dock.setWidget(self._explorer)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, explorer_dock)

        self._inspector = InspectorPanel()
        inspector_dock = QDockWidget("Inspector", self)
        inspector_dock.setObjectName("InspectorDock")
        inspector_dock.setWidget(self._inspector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, inspector_dock)

        self._log_viewer = LogViewer()
        logs_dock = QDockWidget("Logs", self)
        logs_dock.setObjectName("LogsDock")
        logs_dock.setWidget(self._log_viewer)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, logs_dock)

        self._status = AppStatusBar(self, repo_root=self._repo_root)
        self.setStatusBar(self._status)

        self._file_actions = build_file_actions(self)
        self._project_actions = build_project_actions(self)
        self._dataset_actions = build_dataset_actions(self)
        self._pipeline_actions = build_pipeline_actions(self)
        self._view_actions = build_view_actions(self)
        self._help_actions = build_help_actions(self)
        self._toolbar_actions = build_toolbar_actions(self)
        self._build_menus()
        self._build_toolbar()

        self._dock_widgets = {
            "workspace_explorer": explorer_dock,
            "inspector": inspector_dock,
            "logs": logs_dock,
            "results": None,
        }

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self._file_actions["new_workspace"])
        file_menu.addAction(self._file_actions["open_workspace"])
        self._recent_menu = file_menu.addMenu("Recent Workspaces")
        file_menu.addSeparator()
        file_menu.addAction(self._file_actions["exit"])

        project_menu = menu_bar.addMenu("Project")
        for key in ("new_project", "open_project", "project_settings"):
            project_menu.addAction(self._project_actions[key])

        dataset_menu = menu_bar.addMenu("Dataset")
        for key in ("register_dataset", "validate_dataset", "normalize_dataset"):
            dataset_menu.addAction(self._dataset_actions[key])

        pipeline_menu = menu_bar.addMenu("Pipeline")
        for key in ("run_step", "run_all", "stop"):
            pipeline_menu.addAction(self._pipeline_actions[key])

        view_menu = menu_bar.addMenu("View")
        for key in ("workspace_explorer", "inspector", "logs", "results"):
            view_menu.addAction(self._view_actions[key])

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(self._help_actions["about"])

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setObjectName("MainToolbar")
        self.addToolBar(toolbar)
        for key in ("open_workspace", "new_project", "register_dataset", "run_pipeline", "refresh"):
            toolbar.addAction(self._toolbar_actions[key])

    def _connect_signals(self) -> None:
        self._file_actions["new_workspace"].triggered.connect(self._on_new_workspace)
        self._file_actions["open_workspace"].triggered.connect(self._on_open_workspace)
        self._file_actions["exit"].triggered.connect(self.close)
        self._project_actions["new_project"].triggered.connect(self._on_new_project)
        self._project_actions["open_project"].triggered.connect(self._on_open_project)
        self._project_actions["project_settings"].triggered.connect(
            lambda: self._placeholder("Project settings")
        )
        self._dataset_actions["register_dataset"].triggered.connect(self._on_register_dataset)
        self._dataset_actions["validate_dataset"].triggered.connect(
            lambda: self._placeholder("Validate dataset")
        )
        self._dataset_actions["normalize_dataset"].triggered.connect(
            lambda: self._placeholder("Normalize dataset")
        )
        self._pipeline_actions["run_step"].triggered.connect(self._pipeline_controller.run_selected_step)
        self._pipeline_actions["run_all"].triggered.connect(self._pipeline_controller.run_all)
        self._pipeline_actions["stop"].triggered.connect(self._pipeline_controller.stop)
        self._toolbar_actions["open_workspace"].triggered.connect(self._on_open_workspace)
        self._toolbar_actions["new_project"].triggered.connect(self._on_new_project)
        self._toolbar_actions["register_dataset"].triggered.connect(self._on_register_dataset)
        self._toolbar_actions["run_pipeline"].triggered.connect(self._pipeline_controller.run_all)
        self._toolbar_actions["refresh"].triggered.connect(self._refresh_ui)
        self._help_actions["about"].triggered.connect(self._show_about)

        self._view_actions["workspace_explorer"].triggered.connect(
            lambda: self._toggle_dock("workspace_explorer")
        )
        self._view_actions["inspector"].triggered.connect(lambda: self._toggle_dock("inspector"))
        self._view_actions["logs"].triggered.connect(lambda: self._toggle_dock("logs"))
        self._view_actions["results"].triggered.connect(self._show_results_panel)

        self._welcome.new_workspace_requested.connect(self._on_new_workspace)
        self._welcome.open_workspace_requested.connect(self._on_open_workspace)
        self._explorer.project_selected.connect(self._project_controller.select_project)
        self._explorer.dataset_selected.connect(self._dataset_controller.select_dataset)
        self._explorer.workspace_selected.connect(self._on_workspace_selected)

        self._workspace_controller.message.connect(self._log)
        self._workspace_controller.error.connect(self._show_error)
        self._workspace_controller.workspace_opened.connect(lambda _: self._refresh_ui())
        self._workspace_controller.workspace_closed.connect(self._refresh_ui)
        self._project_controller.message.connect(self._log)
        self._project_controller.error.connect(self._show_error)
        self._project_controller.project_selected.connect(self._on_project_selected)
        self._dataset_controller.message.connect(self._log)
        self._dataset_controller.error.connect(self._show_error)
        self._dataset_controller.dataset_selected.connect(self._on_dataset_selected)
        self._pipeline_controller.message.connect(self._log)

    def closeEvent(self, event) -> None:
        app_settings.save_window_geometry(self)
        super().closeEvent(event)

    def _log(self, message: str) -> None:
        self._log_viewer.append(message)

    def _show_error(self, message: str) -> None:
        self._log(f"ERROR: {message}")
        QMessageBox.warning(self, APP_TITLE, message)

    def _placeholder(self, feature: str) -> None:
        self._log(f"{feature} — coming in a later desktop release.")

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            f"{APP_TITLE}\nVersion {__version__}\nDesktop application foundation.",
        )

    def _toggle_dock(self, key: str) -> None:
        dock = self._dock_widgets.get(key)
        if dock is not None:
            dock.setVisible(not dock.isVisible())

    def _show_results_panel(self) -> None:
        self._stack.setCurrentWidget(self._results_panel)

    def _on_new_workspace(self) -> None:
        dialog = NewWorkspaceDialog(self, initial_location=str(Path.home()))
        if dialog.exec():
            self._workspace_controller.create_workspace(dialog.location(), dialog.workspace_name())

    def _on_open_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Workspace Folder", str(Path.home()))
        if path:
            self._workspace_controller.open_workspace(Path(path))

    def _on_new_project(self) -> None:
        workspace = self._state.workspace
        if workspace is None:
            self._show_error("Open a workspace first.")
            return
        dialog = NewProjectDialog(self, datasets=workspace.list_datasets())
        if dialog.exec():
            self._project_controller.create_project(
                workspace,
                name=dialog.project_name(),
                description=dialog.description(),
                dataset_id=dialog.dataset_id(),
                adapter=dialog.adapter(),
            )
            self._refresh_ui()

    def _on_open_project(self) -> None:
        self._placeholder("Open project from explorer")

    def _on_register_dataset(self) -> None:
        workspace = self._state.workspace
        if workspace is None:
            self._show_error("Open a workspace first.")
            return
        dialog = RegisterDatasetDialog(self)
        if dialog.exec():
            self._dataset_controller.register_dataset(
                workspace,
                dataset_id=dialog.dataset_id(),
                source=dialog.source(),
                adapter=dialog.adapter(),
                raw_directory=dialog.raw_directory(),
            )
            self._refresh_ui()

    def _on_workspace_selected(self) -> None:
        if self._state.workspace is not None:
            self._state.selection_kind = "workspace"
            self._stack.setCurrentWidget(self._welcome)
            self._refresh_ui()

    def _on_project_selected(self, project) -> None:
        self._project_overview.show_project(project)
        self._pipeline_panel.show_steps(self._pipeline_controller.list_steps())
        self._stack.setCurrentWidget(self._project_overview)
        self._refresh_ui()

    def _on_dataset_selected(self, dataset) -> None:
        self._dataset_overview.show_dataset(dataset)
        self._stack.setCurrentWidget(self._dataset_overview)
        self._refresh_ui()

    def _refresh_recent_menu(self) -> None:
        if self._recent_menu is None:
            return
        self._recent_menu.clear()
        entries = self._workspace_controller.recent_workspaces()
        if not entries:
            action = self._recent_menu.addAction("(empty)")
            action.setEnabled(False)
            return
        for entry in entries:
            label = str(entry.get("name", entry.get("path", "workspace")))
            path = Path(str(entry["path"]))

            def _open(checked=False, p=path) -> None:
                self._workspace_controller.open_workspace(p)

            self._recent_menu.addAction(label, _open)

    def _refresh_ui(self) -> None:
        workspace = self._state.workspace
        self._explorer.refresh(workspace)
        self._status.update_state(self._state)
        self._inspector.update_state(self._state)
        self._refresh_recent_menu()
        if workspace is None:
            self._stack.setCurrentWidget(self._welcome)
        elif self._state.selection_kind == "project" and self._state.project is not None:
            self._project_overview.show_project(self._state.project)
            self._pipeline_panel.show_steps(self._pipeline_controller.list_steps())
            self._stack.setCurrentWidget(self._project_overview)
        elif self._state.selection_kind == "dataset" and self._state.dataset is not None:
            self._dataset_overview.show_dataset(self._state.dataset)
            self._stack.setCurrentWidget(self._dataset_overview)
