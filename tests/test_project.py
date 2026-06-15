"""Tests for project management."""

from pathlib import Path

from tcr_bcr_tools.project import Project, Workspace, load_yaml


def test_project_load_save(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("JIA_Pilot", name="JIA Pilot")

    reloaded = Project(project.root, "JIA_Pilot")
    data = reloaded.load()

    assert data["project"]["name"] == "JIA Pilot"
    assert data["tool"]["version"]


def test_set_and_get_status(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("JIA_Pilot")

    project.set_status("extract_annotations", "done")
    project.set_status("roc_auc", "pending")

    assert project.get_status("extract_annotations") == "done"
    assert project.get_status()["roc_auc"] == "pending"


def test_add_output(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("JIA_Pilot")

    path = project.add_output("paired_detection_table.csv", "patient,clone\n")
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("patient")


def test_add_figure(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("JIA_Pilot")

    path = project.add_figure("detection_curve.png", b"PNG")
    assert path.exists()


def test_add_log(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project("JIA_Pilot")

    path = project.add_log("run.log", "started\n")
    assert path.exists()


def test_project_yaml_roundtrip(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project(
        "JIA_Pilot",
        name="JIA Pilot",
        description="Pilot analysis of GSE160097",
        datasets=["GSE160097"],
        adapter="tenx",
        analysis="detection",
        status={"extract_annotations": "done"},
    )

    loaded = load_yaml(project.manifest_path)
    assert loaded["datasets"] == ["GSE160097"]
    assert loaded["adapter"] == "tenx"
    assert loaded["status"]["extract_annotations"] == "done"
