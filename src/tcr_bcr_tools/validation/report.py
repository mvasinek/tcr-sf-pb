"""Validation result and report models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from tcr_bcr_tools.validation.severity import Severity
from tcr_bcr_tools.validation.summary import ValidationSummary

VALIDATION_REPORT_FILE = "validation_report.yaml"
VALIDATION_SUMMARY_FILE = "validation_summary.json"


@dataclass
class ValidationResult:
    """Outcome of one validation rule."""

    rule_id: str
    severity: Severity
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    affected_rows: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "affected_rows": self.affected_rows,
        }


@dataclass
class ValidationReport:
    """Full dataset validation report."""

    dataset_id: str
    adapter: str
    timestamp: str
    tool_version: str
    git_branch: str
    git_commit: str
    git_tag: str
    results: list[ValidationResult]
    summary: ValidationSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "adapter": self.adapter,
            "timestamp": self.timestamp,
            "tool_version": self.tool_version,
            "git": {
                "branch": self.git_branch,
                "commit": self.git_commit,
                "tag": self.git_tag,
            },
            "results": [result.to_dict() for result in self.results],
            "summary": asdict(self.summary),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationReport:
        git = data.get("git", {})
        summary_data = data.get("summary", {})
        results = [
            ValidationResult(
                rule_id=item["rule_id"],
                severity=Severity(item["severity"]),
                passed=bool(item["passed"]),
                message=str(item.get("message", "")),
                details=dict(item.get("details", {})),
                affected_rows=int(item.get("affected_rows", 0)),
            )
            for item in data.get("results", [])
        ]
        summary = ValidationSummary(
            passed=int(summary_data.get("passed", 0)),
            failed=int(summary_data.get("failed", 0)),
            warnings=int(summary_data.get("warnings", 0)),
            errors=int(summary_data.get("errors", 0)),
            critical=int(summary_data.get("critical", 0)),
            score=int(summary_data.get("score", 0)),
        )
        return cls(
            dataset_id=str(data.get("dataset_id", "")),
            adapter=str(data.get("adapter", "")),
            timestamp=str(data.get("timestamp", "")),
            tool_version=str(data.get("tool_version", "")),
            git_branch=str(git.get("branch", "unknown")),
            git_commit=str(git.get("commit", "unknown")),
            git_tag=str(git.get("tag", "unknown")),
            results=results,
            summary=summary,
        )


def save_validation_report(report: ValidationReport, path: Path) -> None:
    """Serialize a validation report to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(report.to_dict(), handle, sort_keys=False)


def load_validation_report(path: Path) -> ValidationReport:
    """Load a validation report from YAML."""
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return ValidationReport.from_dict(data)
