"""Desktop package import smoke tests."""

from __future__ import annotations

import importlib


def test_import_desktop_app() -> None:
    module = importlib.import_module("tcr_bcr_tools.desktop.app")
    assert callable(module.main)


def test_import_pyside6() -> None:
    importlib.import_module("PySide6.QtWidgets")


def test_import_desktop_controllers() -> None:
    importlib.import_module("tcr_bcr_tools.desktop.controllers.workspace_controller")


def test_import_desktop_widgets() -> None:
    importlib.import_module("tcr_bcr_tools.desktop.widgets.workspace_explorer")
