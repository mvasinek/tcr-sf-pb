"""Tests for workspace management."""

from pathlib import Path

from tcr_bcr_tools.project import Workspace, load_yaml, save_yaml


def test_create_workspace(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "workspace")
    settings = workspace.load()

    assert workspace.settings_path.exists()
    assert workspace.datasets_dir.is_dir()
    assert workspace.projects_dir.is_dir()
    assert settings["workspace"]["version"]


def test_save_and_load_settings_yaml(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    data = {"workspace": {"version": "0.5.0"}, "default_project": "demo"}
    save_yaml(path, data)

    loaded = load_yaml(path)
    assert loaded["default_project"] == "demo"


def test_create_project(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project(
        "JIA_Pilot",
        name="JIA Pilot",
        description="Pilot analysis",
        datasets=["GSE160097"],
        analysis="detection",
    )

    assert (project.root / "project.yaml").exists()
    assert project.outputs_dir.is_dir()
    assert "JIA_Pilot" in workspace.list_projects()


def test_list_projects(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    workspace.create_project("alpha")
    workspace.create_project("beta")

    assert workspace.list_projects() == ["alpha", "beta"]


def test_create_dataset(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset(
        "GSE160097",
        title="GSE160097",
        source="GEO",
        adapter="tenx",
    )

    assert (dataset.root / "dataset.yaml").exists()
    assert dataset.raw_dir.is_dir()
    assert "GSE160097" in workspace.list_datasets()


def test_list_datasets(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    workspace.create_dataset("GSE160097")
    workspace.create_dataset("GSE999999")

    assert workspace.list_datasets() == ["GSE160097", "GSE999999"]


def test_open_project(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    workspace.create_project("JIA_Pilot")
    project = workspace.open_project("JIA_Pilot")

    assert project.project_id == "JIA_Pilot"
    assert project.manifest_path.exists()


def test_multiple_projects_one_dataset(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    workspace.create_dataset("GSE160097")

    workspace.create_project("project_a", datasets=["GSE160097"])
    workspace.create_project("project_b", datasets=["GSE160097"])

    assert workspace.list_projects() == ["project_a", "project_b"]
    assert workspace.list_datasets() == ["GSE160097"]
