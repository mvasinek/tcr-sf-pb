"""Desktop application settings via QSettings."""

from __future__ import annotations

from PySide6.QtCore import QSettings

ORGANIZATION = "VSB-TUO"
APPLICATION = "tcr-sf-pb"


def get_settings() -> QSettings:
    """Return application QSettings instance."""
    return QSettings(ORGANIZATION, APPLICATION)


def last_workspace() -> str:
    """Return last opened workspace path or empty string."""
    value = get_settings().value("workspace/last_path", "")
    return str(value) if value else ""


def set_last_workspace(path: str) -> None:
    """Persist last opened workspace path."""
    settings = get_settings()
    settings.setValue("workspace/last_path", path)
    settings.sync()


def save_window_geometry(window) -> None:
    """Save main window geometry and state."""
    settings = get_settings()
    settings.setValue("window/geometry", window.saveGeometry())
    settings.setValue("window/state", window.saveState())
    settings.sync()


def restore_window_geometry(window) -> None:
    """Restore main window geometry and state when available."""
    settings = get_settings()
    geometry = settings.value("window/geometry")
    state = settings.value("window/state")
    if geometry:
        window.restoreGeometry(geometry)
    if state:
        window.restoreState(state)
