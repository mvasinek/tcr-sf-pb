"""Tests for validation GUI helpers."""

from tcr_bcr_tools.gui.validation_helpers import severity_color, status_label


def test_status_label() -> None:
    assert status_label(True) == "PASS"
    assert status_label(False) == "FAIL"


def test_severity_color() -> None:
    assert severity_color("ERROR") == "red"
    assert severity_color("UNKNOWN") == "gray"
