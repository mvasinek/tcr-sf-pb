"""Tests for gallery helpers."""

from tcr_bcr_tools.gui.gallery import list_figure_entries, list_table_entries
from tcr_bcr_tools.project import Workspace


def test_gallery_lists(tmp_path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("demo")
    registry = project.output_registry(workspace.root)
    csv_file = project.add_output("a.csv", "x\n")
    png_file = project.add_figure("a.png", b"PNG")
    registry.register_output(
        path=str(csv_file.relative_to(workspace.root)),
        name="a.csv",
        analysis="roc_auc",
        output_type="csv",
    )
    registry.register_output(
        path=str(png_file.relative_to(workspace.root)),
        name="a.png",
        analysis="roc_auc",
        output_type="png",
    )
    assert [entry.name for entry in list_table_entries(registry)] == ["a.csv"]
    assert [entry.name for entry in list_figure_entries(registry)] == ["a.png"]
