"""Validation severity levels."""

from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    """Severity of a validation finding."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def blocks_pipeline(self) -> bool:
        """Return True when pipeline must stop without user override."""
        return self == Severity.CRITICAL

    def requires_confirmation(self) -> bool:
        """Return True when user confirmation is required to continue."""
        return self == Severity.ERROR
