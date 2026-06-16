"""Application log viewer."""

from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class LogViewer(QWidget):
    """Read-only log output for desktop shell events."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        layout.addWidget(self._text)

    def append(self, message: str) -> None:
        self._text.appendPlainText(message)

    def clear(self) -> None:
        self._text.clear()
