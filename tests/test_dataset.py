"""Tests for dataset management."""

from pathlib import Path

from tcr_bcr_tools.project import Dataset, Workspace, load_yaml


def test_dataset_load_save(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", source="GEO", adapter="tenx")

    reloaded = Dataset(dataset.root, "GSE160097")
    data = reloaded.load()

    assert data["dataset"]["id"] == "GSE160097"
    assert data["dataset"]["adapter"] == "tenx"


def test_dataset_validate_success(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097")

    errors = dataset.validate()
    assert errors == []


def test_dataset_validate_missing_manifest(tmp_path: Path) -> None:
    dataset = Dataset(tmp_path / "GSE160097", "GSE160097")
    errors = dataset.validate()
    assert any("Missing manifest" in error for error in errors)


def test_dataset_adapter_name(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", adapter="tenx")

    assert dataset.adapter() == "tenx"


def test_dataset_yaml_roundtrip(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset(
        "GSE160097",
        title="GSE160097",
        source="GEO",
        adapter="tenx",
    )

    loaded = load_yaml(dataset.manifest_path)
    assert loaded["files"]["raw"] == "raw/"
    assert loaded["files"]["intermediate"] == "intermediate/"


def test_manifest_serialization(tmp_path: Path) -> None:
    from tcr_bcr_tools.project.manifest import save_yaml

    path = tmp_path / "nested" / "dataset.yaml"
    payload = {"dataset": {"id": "GSE160097"}}
    save_yaml(path, payload)

    assert load_yaml(path)["dataset"]["id"] == "GSE160097"
