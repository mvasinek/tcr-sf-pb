"""Headless MainWindow smoke tests."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QDockWidget, QToolBar

from tcr_bcr_tools.desktop.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_window_creates(qapp) -> None:
    window = MainWindow()
    assert window.windowTitle()
    window.close()


def test_main_window_has_file_menu(qapp) -> None:
    window = MainWindow()
    menus = [action.text() for action in window.menuBar().actions()]
    assert "File" in menus
    window.close()


def test_main_window_has_toolbar(qapp) -> None:
    window = MainWindow()
    toolbars = window.findChildren(QToolBar)
    assert toolbars
    window.close()


def test_main_window_has_workspace_explorer_dock(qapp) -> None:
    window = MainWindow()
    docks = window.findChildren(QDockWidget)
    assert any(dock.objectName() == "WorkspaceExplorerDock" for dock in docks)
    window.close()


def test_main_window_has_status_bar(qapp) -> None:
    window = MainWindow()
    assert window.statusBar() is not None
    window.close()


def test_main_window_closes_cleanly(qapp) -> None:
    window = MainWindow()
    window.close()
    assert not window.isVisible()
