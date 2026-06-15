"""Session state helpers for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tcr_bcr_tools.gui.constants import DEFAULT_WORKSPACE_NAME, SESSION_KEYS


def default_session_state(home: Path | None = None) -> dict[str, Any]:
    """Return default session state mapping."""
    workspace_home = home or Path.home()
    return {
        "workspace_path": str(workspace_home / DEFAULT_WORKSPACE_NAME),
        "workspace": None,
        "selected_project": "",
        "selected_dataset": "",
        "show_create_project": False,
        "show_register_dataset": False,
        "show_settings": False,
        "show_logs": False,
        "show_about": False,
        "selected_pipeline_step": "",
        "force_recompute": False,
    }


def init_session_state(state: dict[str, Any], home: Path | None = None) -> None:
    """Populate missing session state keys."""
    for key, value in default_session_state(home).items():
        state.setdefault(key, value)


def serialize_session_state(state: dict[str, Any]) -> dict[str, str]:
    """Serialize session selections for persistence/testing."""
    return {
        key: str(state.get(key, ""))
        for key in SESSION_KEYS
        if key != "workspace"
    }


def apply_session_update(state: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Apply updates to a session-like mapping."""
    merged = dict(state)
    merged.update(updates)
    return merged
