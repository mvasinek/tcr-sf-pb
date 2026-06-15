"""Tests for the output registry API."""

from pathlib import Path

import yaml

from tcr_bcr_tools.project import Project, Workspace
from tcr_bcr_tools.project.output_registry import OutputRegistry, infer_output_type


def test_register_and_find_output(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("demo")
    registry = project.output_registry(workspace.root)
    output_file = project.add_output("tables/demo.csv", "a,b\n1,2\n")
    rel_path = str(output_file.relative_to(workspace.root))
    entry = registry.register_output(
        path=rel_path,
        name="demo.csv",
        analysis="detection_curves",
        output_type="csv",
        pipeline_step="detection_curves",
        description="Demo table",
        git_branch="main",
        git_commit="abc",
        git_tag="v0.5.5",
    )
    found = registry.find_output(entry.id)
    assert found is not None
    assert found.name == "demo.csv"
    assert found.git_commit == "abc"


def test_list_analysis_outputs(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("demo")
    registry = project.output_registry(workspace.root)
    file_a = project.add_output("roc/roc.csv", "x\n")
    file_b = project.add_figure("roc/roc.png", b"PNG")
    registry.register_output(
        path=str(file_a.relative_to(workspace.root)),
        name="roc.csv",
        analysis="roc_auc",
        output_type="csv",
        pipeline_step="roc_auc",
    )
    registry.register_output(
        path=str(file_b.relative_to(workspace.root)),
        name="roc.png",
        analysis="roc_auc",
        output_type="png",
        pipeline_step="roc_auc",
    )
    outputs = registry.list_analysis_outputs("roc_auc")
    assert len(outputs) == 2


def test_search_favorite_recent_and_export(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("demo")
    registry = project.output_registry(workspace.root)
    output_file = project.add_output("detection/summary.csv", "value\n1\n")
    rel = str(output_file.relative_to(workspace.root))
    entry = registry.register_output(
        path=rel,
        name="summary.csv",
        analysis="detection_curves",
        output_type="csv",
        pipeline_step="detection_curves",
        description="Detection summary",
    )
    matches = registry.search_outputs("summary")
    assert len(matches) == 1
    registry.favorite(entry.id)
    assert registry.is_favorite(entry.id)
    registry.record_recent(entry.id)
    assert registry.recent()[0]["id"] == entry.id
    zip_path = project.cache_dir / "export.zip"
    registry.export_zip([entry.id], zip_path)
    assert zip_path.exists()


def test_registry_serialization(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("demo")
    registry = project.output_registry(workspace.root)
    output_file = project.add_output("demo.csv", "x\n")
    registry.register_output(
        path=str(output_file.relative_to(workspace.root)),
        name="demo.csv",
        analysis="demo",
        output_type="csv",
    )
    raw = yaml.safe_load(project.manifest_path.read_text(encoding="utf-8"))
    assert isinstance(raw["output_registry"], list)
    assert raw["output_registry"][0]["name"] == "demo.csv"


def test_infer_output_type(tmp_path: Path) -> None:
    assert infer_output_type(tmp_path / "a.csv") == "csv"
    assert infer_output_type(tmp_path / "a.png") == "png"
    assert infer_output_type(tmp_path / "a.yaml") == "yaml"
