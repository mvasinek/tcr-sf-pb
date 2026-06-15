"""Dataset validation orchestration."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from tcr_bcr_tools import __version__
from tcr_bcr_tools.git_info import get_git_summary
from tcr_bcr_tools.validation.report import (
    VALIDATION_REPORT_FILE,
    VALIDATION_SUMMARY_FILE,
    ValidationReport,
    save_validation_report,
)
from tcr_bcr_tools.validation.rules import ValidationContext, ValidationRule, default_rules
from tcr_bcr_tools.validation.severity import Severity
from tcr_bcr_tools.validation.summary import compute_summary


class ValidationGateError(Exception):
    """Raised when dataset validation blocks pipeline execution."""

    def __init__(self, message: str, report: ValidationReport | None = None) -> None:
        super().__init__(message)
        self.report = report


class DatasetValidator:
    """Run validation rules against a unified annotation table."""

    def __init__(self, rules: list[ValidationRule] | None = None) -> None:
        self.rules = rules or default_rules()

    def validate(self, context: ValidationContext) -> list:
        results = []
        for rule in self.rules:
            if (
                results
                and results[0].rule_id == "required_columns"
                and not results[0].passed
            ):
                break
            results.append(rule.validate(context))
        return results

    def run(
        self,
        *,
        dataset_id: str,
        adapter: str,
        adapter_version: str,
        df: pd.DataFrame,
        repo_root: Path | None = None,
    ) -> ValidationReport:
        context = ValidationContext(
            dataset_id=dataset_id,
            adapter=adapter,
            adapter_version=adapter_version,
            df=df,
        )
        results = self.validate(context)
        git = get_git_summary(repo_root)
        return ValidationReport(
            dataset_id=dataset_id,
            adapter=adapter,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            tool_version=__version__,
            git_branch=git.get("branch", "unknown"),
            git_commit=git.get("commit", "unknown"),
            git_tag=git.get("tag", "unknown"),
            results=results,
            summary=compute_summary(results),
        )


def save_validation_summary(report: ValidationReport, path: Path) -> None:
    """Serialize validation summary to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset_id": report.dataset_id,
        "adapter": report.adapter,
        "timestamp": report.timestamp,
        "summary": {
            "passed": report.summary.passed,
            "failed": report.summary.failed,
            "warnings": report.summary.warnings,
            "errors": report.summary.errors,
            "critical": report.summary.critical,
            "score": report.summary.score,
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def quality_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Compute dataset quality metrics for dashboards."""
    compartments = df["compartment"].astype(str).map(
        lambda value: value if value in {"SF", "blood"} else value
    )
    productive = df["productive"].fillna(False).astype(bool)
    high_conf = df["high_confidence"].fillna(False).astype(bool)
    return {
        "patients": int(df["patient"].nunique()),
        "cells": int(df["barcode"].nunique()),
        "clonotypes": int(df[["patient", "barcode"]].drop_duplicates().shape[0]),
        "sf_samples": int((compartments == "SF").sum()),
        "blood_samples": int((compartments == "blood").sum()),
        "cell_types": df["cell_type"].astype(str).value_counts().to_dict(),
        "productive_fraction": round(float(productive.mean()), 4),
        "high_confidence_fraction": round(float(high_conf.mean()), 4),
        "mean_reads": round(float(df["reads"].mean()), 2),
        "mean_umis": round(float(df["umis"].mean()), 2),
    }


def report_allows_pipeline(
    report: ValidationReport,
    *,
    ignore_errors: bool = False,
) -> tuple[bool, str]:
    """Return whether pipeline execution may continue."""
    if report.summary.critical > 0:
        return False, "Critical validation issues block the pipeline."
    if report.summary.errors > 0 and not ignore_errors:
        return (
            False,
            "Validation errors require explicit confirmation to continue.",
        )
    return True, ""


def main() -> None:
    import argparse

    from tcr_bcr_tools.adapters.schema import UNIFIED_ANNOTATIONS_FILE
    from tcr_bcr_tools.project.dataset import Dataset

    parser = argparse.ArgumentParser(description="Validate a dataset unified table.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()

    dataset = Dataset(args.dataset, args.dataset.name)
    report = dataset.validate(repo_root=args.repo_root)
    print(f"Validation score: {report.summary.score}/100")
    print(
        f"passed={report.summary.passed} warnings={report.summary.warnings} "
        f"errors={report.summary.errors} critical={report.summary.critical}"
    )
    unified = args.dataset / "intermediate" / UNIFIED_ANNOTATIONS_FILE
    if not unified.exists():
        raise SystemExit("Unified annotations not found after validation.")
    allowed, reason = report_allows_pipeline(report)
    if not allowed:
        raise SystemExit(reason)


if __name__ == "__main__":
    main()
