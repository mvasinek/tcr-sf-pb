"""Tests for output search helpers."""

from tcr_bcr_tools.gui.search import search_registry
from tcr_bcr_tools.project import Workspace


def test_search_outputs(tmp_path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("demo")
    registry = project.output_registry(workspace.root)
    output_file = project.add_output("detection_curve.csv", "x\n")
    registry.register_output(
        path=str(output_file.relative_to(workspace.root)),
        name="detection_curve.csv",
        analysis="detection_curves",
        output_type="csv",
        description="Detection curve table",
    )
    by_name = search_registry(registry, "detection")
    by_type = search_registry(registry, "csv")
    assert len(by_name) == 1
    assert len(by_type) == 1
