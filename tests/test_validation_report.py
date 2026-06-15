"""Tests for validation report serialization."""

from pathlib import Path

import yaml

from tcr_bcr_tools.validation.report import (
    ValidationReport,
    ValidationResult,
    load_validation_report,
    save_validation_report,
)
from tcr_bcr_tools.validation.severity import Severity
from tcr_bcr_tools.validation.summary import ValidationSummary


def test_validation_report_roundtrip(tmp_path: Path) -> None:
    report = ValidationReport(
        dataset_id="GSE160097",
        adapter="tenx",
        timestamp="2026-06-15T10:00:00",
        tool_version="0.5.4",
        git_branch="main",
        git_commit="abc123",
        git_tag="v0.5.4",
        results=[
            ValidationResult(
                rule_id="required_columns",
                severity=Severity.INFO,
                passed=True,
                message="ok",
            )
        ],
        summary=ValidationSummary(
            passed=1,
            failed=0,
            warnings=0,
            errors=0,
            critical=0,
            score=100,
        ),
    )
    path = tmp_path / "validation_report.yaml"
    save_validation_report(report, path)
    loaded = load_validation_report(path)
    assert loaded.dataset_id == "GSE160097"
    assert loaded.summary.score == 100
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert raw["git"]["commit"] == "abc123"
