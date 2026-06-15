"""Tests for results browser helpers."""

from pathlib import Path

from tcr_bcr_tools.gui.gallery import list_figure_entries, list_table_entries
from tcr_bcr_tools.gui.search import search_registry
from tcr_bcr_tools.project import Workspace


def test_results_browser_helpers(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("demo")
    registry = project.output_registry(workspace.root)
    csv_file = project.add_output("tables/a.csv", "x\n")
    png_file = project.add_figure("figs/a.png", b"PNG")
    registry.register_output(
        path=str(csv_file.relative_to(workspace.root)),
        name="a.csv",
        analysis="detection_curves",
        output_type="csv",
    )
    registry.register_output(
        path=str(png_file.relative_to(workspace.root)),
        name="a.png",
        analysis="detection_curves",
        output_type="png",
    )
    assert len(list_table_entries(registry)) == 1
    assert len(list_figure_entries(registry)) == 1
    assert search_registry(registry, "a.csv")[0].name == "a.csv"
