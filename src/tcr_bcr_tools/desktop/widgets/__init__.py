"""Desktop widgets."""

from tcr_bcr_tools.desktop.widgets.dataset_overview import DatasetOverview
from tcr_bcr_tools.desktop.widgets.inspector_panel import InspectorPanel
from tcr_bcr_tools.desktop.widgets.log_viewer import LogViewer
from tcr_bcr_tools.desktop.widgets.pipeline_panel import PipelinePanel
from tcr_bcr_tools.desktop.widgets.project_overview import ProjectOverview
from tcr_bcr_tools.desktop.widgets.results_panel import ResultsPanel
from tcr_bcr_tools.desktop.widgets.status_bar import AppStatusBar
from tcr_bcr_tools.desktop.widgets.welcome_panel import WelcomePanel
from tcr_bcr_tools.desktop.widgets.workspace_explorer import WorkspaceExplorer

__all__ = [
    "AppStatusBar",
    "DatasetOverview",
    "InspectorPanel",
    "LogViewer",
    "PipelinePanel",
    "ProjectOverview",
    "ResultsPanel",
    "WelcomePanel",
    "WorkspaceExplorer",
]
