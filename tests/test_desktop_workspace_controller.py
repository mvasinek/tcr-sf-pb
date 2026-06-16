"""WorkspaceController tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tcr_bcr_tools.desktop.controllers.workspace_controller import (
    WorkspaceController,
    validate_workspace,
)
from tcr_bcr_tools.desktop.state import DesktopState
from tcr_bcr_tools.project import Workspace
from tcr_bcr_tools.project.recent_workspaces import load_recent_workspaces


@pytest.fixture
def recent_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_dir = tmp_path / ".tcr_sf_pb"
    recent_file = config_dir / "recent_workspaces.yaml"
    monkeypatch.setattr("tcr_bcr_tools.project.recent_workspaces.USER_CONFIG_DIR", config_dir)
    monkeypatch.setattr("tcr_bcr_tools.project.recent_workspaces.RECENT_WORKSPACES_FILE", recent_file)
    return config_dir


def test_validate_workspace_success(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "demo")
    workspace.load()
    valid, message = validate_workspace(workspace.root)
    assert valid is True
    assert message == ""


def test_validate_workspace_missing(tmp_path: Path) -> None:
    valid, message = validate_workspace(tmp_path / "missing")
    assert valid is False


def test_workspace_controller_open(recent_config: Path, tmp_path: Path) -> None:
    workspace_root = tmp_path / "opened"
    Workspace(workspace_root).load()
    state = DesktopState()
    controller = WorkspaceController(state)
    assert controller.open_workspace(workspace_root) is True
    assert state.workspace is not None
    assert load_recent_workspaces()[0]["name"] == "opened"


def test_workspace_controller_create(recent_config: Path, tmp_path: Path) -> None:
    state = DesktopState()
    controller = WorkspaceController(state)
    assert controller.create_workspace(tmp_path, "new-ws") is True
    assert state.workspace is not None
    assert (tmp_path / "new-ws" / "settings.yaml").exists()


def test_project_selection_updates_state(recent_config: Path, tmp_path: Path) -> None:
    from tcr_bcr_tools.desktop.controllers.project_controller import ProjectController

    workspace = Workspace(tmp_path)
    workspace.load()
    workspace.create_project("demo", name="Demo")
    state = DesktopState()
    state.set_workspace(workspace)
    project_controller = ProjectController(state)
    assert project_controller.select_project("demo") is True
    assert state.project_id == "demo"
    assert state.selection_kind == "project"
