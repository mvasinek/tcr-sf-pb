"""Validation score and summary computation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tcr_bcr_tools.validation.severity import Severity

if TYPE_CHECKING:
    from tcr_bcr_tools.validation.report import ValidationResult


@dataclass
class ValidationSummary:
    """Aggregate validation statistics."""

    passed: int
    failed: int
    warnings: int
    errors: int
    critical: int
    score: int


def compute_summary(results: list[ValidationResult]) -> ValidationSummary:
    passed = sum(1 for result in results if result.passed)
    failed = sum(1 for result in results if not result.passed)
    warnings = sum(
        1
        for result in results
        if not result.passed and result.severity == Severity.WARNING
    )
    errors = sum(
        1
        for result in results
        if not result.passed and result.severity == Severity.ERROR
    )
    critical = sum(
        1
        for result in results
        if not result.passed and result.severity == Severity.CRITICAL
    )
    penalty = critical * 25 + errors * 15 + warnings * 5
    score = max(0, min(100, 100 - penalty))
    return ValidationSummary(
        passed=passed,
        failed=failed,
        warnings=warnings,
        errors=errors,
        critical=critical,
        score=score,
    )
