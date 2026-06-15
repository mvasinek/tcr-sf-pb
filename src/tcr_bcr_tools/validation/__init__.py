"""Centralized dataset validation framework."""

from tcr_bcr_tools.validation.report import (
    VALIDATION_REPORT_FILE,
    VALIDATION_SUMMARY_FILE,
    ValidationReport,
    ValidationResult,
    load_validation_report,
    save_validation_report,
)
from tcr_bcr_tools.validation.rules import ValidationContext, ValidationRule, default_rules
from tcr_bcr_tools.validation.severity import Severity
from tcr_bcr_tools.validation.summary import ValidationSummary, compute_summary
from tcr_bcr_tools.validation.validator import (
    DatasetValidator,
    ValidationGateError,
    quality_metrics,
    report_allows_pipeline,
    save_validation_summary,
)

__all__ = [
    "VALIDATION_REPORT_FILE",
    "VALIDATION_SUMMARY_FILE",
    "DatasetValidator",
    "Severity",
    "ValidationContext",
    "ValidationGateError",
    "ValidationReport",
    "ValidationResult",
    "ValidationRule",
    "ValidationSummary",
    "compute_summary",
    "default_rules",
    "load_validation_report",
    "quality_metrics",
    "report_allows_pipeline",
    "save_validation_report",
    "save_validation_summary",
]
