"""Desktop application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from tcr_bcr_tools.desktop.main_window import MainWindow


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    """Launch the PySide6 desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("tcr-sf-pb")
    window = MainWindow(repo_root=_repo_root())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
