"""Recent workspace persistence in user config (~/.tcr_sf_pb)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tcr_bcr_tools.project.manifest import load_yaml, save_yaml
from tcr_bcr_tools.project.workspace import SETTINGS_MANIFEST

USER_CONFIG_DIR = Path.home() / ".tcr_sf_pb"
RECENT_WORKSPACES_FILE = USER_CONFIG_DIR / "recent_workspaces.yaml"
MAX_RECENT_WORKSPACES = 5


def get_workspace_display_name(path: Path) -> str:
    """Return a human-friendly workspace name (settings name or folder name)."""
    root = Path(path).expanduser().resolve()
    settings_path = root / SETTINGS_MANIFEST
    if settings_path.exists():
        try:
            settings = load_yaml(settings_path)
            workspace_settings = settings.get("workspace", {})
            if isinstance(workspace_settings, dict):
                configured_name = workspace_settings.get("name", "")
                if isinstance(configured_name, str) and configured_name.strip():
                    return configured_name.strip()
        except (OSError, ValueError):
            pass
    return root.name


def load_recent_workspaces() -> list[dict[str, Any]]:
    """Load recent workspace entries from user config."""
    if not RECENT_WORKSPACES_FILE.exists():
        return []
    try:
        data = load_yaml(RECENT_WORKSPACES_FILE)
    except (OSError, ValueError):
        return []
    entries = data.get("recent_workspaces", [])
    if not isinstance(entries, list):
        return []
    entries = [entry for entry in entries if isinstance(entry, dict) and entry.get("path")]
    return sorted(entries, key=lambda item: item.get("last_opened", ""), reverse=True)


def save_recent_workspaces(entries: list[dict[str, Any]]) -> None:
    """Persist recent workspace entries to user config."""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    save_yaml(RECENT_WORKSPACES_FILE, {"recent_workspaces": entries})


def _normalize_entry(path: Path, *, name: str | None = None) -> dict[str, str]:
    resolved = Path(path).expanduser().resolve()
    return {
        "name": name or get_workspace_display_name(resolved),
        "path": str(resolved),
        "last_opened": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def add_recent_workspace(path: Path, *, name: str | None = None) -> None:
    """Add or refresh a workspace in the recent list."""
    resolved = str(Path(path).expanduser().resolve())
    entries = load_recent_workspaces()
    entries = [entry for entry in entries if entry.get("path") != resolved]
    entries.insert(0, _normalize_entry(path, name=name))
    entries.sort(key=lambda item: item.get("last_opened", ""), reverse=True)
    save_recent_workspaces(entries[:MAX_RECENT_WORKSPACES])


def remove_recent_workspace(path: Path) -> None:
    """Remove a workspace from the recent list."""
    resolved = str(Path(path).expanduser().resolve())
    entries = [entry for entry in load_recent_workspaces() if entry.get("path") != resolved]
    save_recent_workspaces(entries)
