"""Tests for GUI helpers and workspace integration."""

from pathlib import Path

from tcr_bcr_tools.gui.dialogs import create_project_from_dialog, register_dataset_from_dialog
from tcr_bcr_tools.gui.git_info import (
    get_current_branch,
    get_current_tag,
    get_git_summary,
    get_last_commit,
    git_available,
)
from tcr_bcr_tools.gui.helpers import build_status_rows, format_status
from tcr_bcr_tools.gui.session_state import (
    apply_session_update,
    default_session_state,
    init_session_state,
    serialize_session_state,
)
from tcr_bcr_tools.project import Workspace
from tcr_bcr_tools.project.manifest import load_yaml
from tcr_bcr_tools.project.workspace import Workspace as WorkspaceClass


def test_load_workspace(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    settings = workspace.load()
    assert settings["workspace"]["version"]
    assert workspace.datasets_dir.is_dir()


def test_create_project_via_dialog(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    workspace.create_dataset("GSE160097", source="GEO")

    project = create_project_from_dialog(
        workspace,
        name="JIA Pilot",
        description="Pilot",
        dataset_id="GSE160097",
        adapter="tenx",
    )

    assert project.project_id == "JIA_Pilot"
    assert (project.root / "project.yaml").exists()
    data = load_yaml(project.manifest_path)
    assert data["datasets"] == ["GSE160097"]


def test_register_dataset_via_dialog(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    raw_dir = tmp_path / "external_raw"
    raw_dir.mkdir()
    (raw_dir / "sample.csv").write_text("x", encoding="utf-8")

    dataset = register_dataset_from_dialog(
        workspace,
        dataset_id="GSE160097",
        source="GEO",
        adapter="tenx",
        raw_directory=str(raw_dir),
    )

    assert dataset.dataset_id == "GSE160097"
    loaded = load_yaml(dataset.manifest_path)
    assert loaded["files"]["raw_source"] == str(raw_dir.resolve())
    assert dataset.count_raw_files() == 1


def test_project_yaml_load(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    project = workspace.create_project(
        "demo",
        status={"extract_annotations": "done", "roc_auc": "pending"},
    )
    data = load_yaml(project.manifest_path)
    assert data["status"]["extract_annotations"] == "done"


def test_dataset_yaml_load(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.register_dataset("GSE160097", source="GEO", adapter="tenx")
    data = load_yaml(dataset.manifest_path)
    assert data["dataset"]["id"] == "GSE160097"


def test_build_status_rows() -> None:
    rows = build_status_rows(
        {
            "extract_annotations": "done",
            "roc_auc": "pending",
            "decile_information": "failed",
        }
    )
    assert rows[0]["display"] == "✔"
    assert rows[4]["status"] == "pending"
    assert rows[5]["color"] == "red"


def test_format_status_unknown() -> None:
    display, color = format_status("custom")
    assert display == "custom"
    assert color == "gray"


def test_session_state_helpers() -> None:
    state: dict = {}
    init_session_state(state)
    assert "workspace_path" in state
    serialized = serialize_session_state(state)
    assert "selected_project" in serialized
    updated = apply_session_update(state, {"selected_project": "JIA_Pilot"})
    assert updated["selected_project"] == "JIA_Pilot"


def test_default_session_state() -> None:
    defaults = default_session_state(Path("/tmp"))
    assert defaults["selected_project"] == ""


def test_workspace_slugify() -> None:
    assert WorkspaceClass.slugify_project_id("JIA Pilot") == "JIA_Pilot"


def test_delete_project(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    workspace.create_project("demo")
    workspace.delete_project("demo")
    assert "demo" not in workspace.list_projects()


def test_git_helpers_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if git_available(repo_root):
        assert get_current_branch(repo_root) != "unknown"
        assert get_last_commit(repo_root) != "unknown"
        summary = get_git_summary(repo_root)
        assert summary["available"] == "true"
    else:
        summary = get_git_summary(repo_root)
        assert summary["branch"] == "Git unavailable"


def test_git_helpers_non_repo(tmp_path: Path) -> None:
    assert git_available(tmp_path) is False
    summary = get_git_summary(tmp_path)
    assert summary["available"] == "false"
