"""Formatting helpers for validation dashboards."""

from __future__ import annotations

from tcr_bcr_tools.validation.severity import Severity


SEVERITY_COLORS = {
    Severity.INFO: "blue",
    Severity.WARNING: "orange",
    Severity.ERROR: "red",
    Severity.CRITICAL: "darkred",
}


def severity_color(severity: str) -> str:
    """Return a Streamlit color name for a severity label."""
    try:
        return SEVERITY_COLORS[Severity(severity)]
    except ValueError:
        return "gray"


def status_label(passed: bool) -> str:
    """Return a compact pass/fail label."""
    return "PASS" if passed else "FAIL"
