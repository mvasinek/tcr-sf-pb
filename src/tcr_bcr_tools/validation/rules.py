"""Validation rules for unified annotation datasets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd

from tcr_bcr_tools.adapters.schema import REQUIRED_COLUMNS
from tcr_bcr_tools.build_detection_table import normalize_compartment
from tcr_bcr_tools.validation.report import ValidationResult
from tcr_bcr_tools.validation.severity import Severity

ALLOWED_COMPARTMENTS = {"SF", "blood"}
ALLOWED_CHAINS = {"TRA", "TRB", "TRG", "TRD", "Multi"}
KNOWN_CELL_TYPES = {"CD4", "CD8", "Treg", "Unknown"}


@dataclass
class ValidationContext:
    """Data passed to validation rules."""

    dataset_id: str
    adapter: str
    adapter_version: str
    df: pd.DataFrame


class ValidationRule(ABC):
    """Abstract validation rule."""

    id: str
    name: str
    description: str
    severity: Severity

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        """Run the rule against a dataset context."""


def _result(
    rule: ValidationRule,
    *,
    passed: bool,
    message: str,
    details: dict[str, Any] | None = None,
    affected_rows: int = 0,
    severity: Severity | None = None,
) -> ValidationResult:
    return ValidationResult(
        rule_id=rule.id,
        severity=severity or rule.severity,
        passed=passed,
        message=message,
        details=details or {},
        affected_rows=affected_rows,
    )


class RequiredColumnsRule(ValidationRule):
    id = "required_columns"
    name = "Required columns"
    description = "All unified schema columns must be present."
    severity = Severity.CRITICAL

    def validate(self, context: ValidationContext) -> ValidationResult:
        missing = [col for col in REQUIRED_COLUMNS if col not in context.df.columns]
        if missing:
            return _result(
                self,
                passed=False,
                message=f"Missing required columns: {missing}",
                details={"missing_columns": missing},
            )
        return _result(self, passed=True, message="All required columns present.")


class MissingPatientRule(ValidationRule):
    id = "missing_patient"
    name = "Missing patient"
    description = "Patient must be defined for every row."
    severity = Severity.ERROR

    def validate(self, context: ValidationContext) -> ValidationResult:
        mask = context.df["patient"].astype(str).str.strip().eq("")
        count = int(mask.sum())
        if count:
            return _result(
                self,
                passed=False,
                message=f"{count} rows have empty patient values.",
                affected_rows=count,
            )
        return _result(self, passed=True, message="All rows have patient values.")


class MissingCompartmentRule(ValidationRule):
    id = "missing_compartment"
    name = "Missing compartment"
    description = "Compartment must be defined."
    severity = Severity.ERROR

    def validate(self, context: ValidationContext) -> ValidationResult:
        mask = context.df["compartment"].isna() | context.df["compartment"].astype(
            str
        ).str.strip().eq("")
        count = int(mask.sum())
        if count:
            return _result(
                self,
                passed=False,
                message=f"{count} rows have missing compartment values.",
                affected_rows=count,
            )
        return _result(self, passed=True, message="All rows have compartment values.")


class AllowedCompartmentValuesRule(ValidationRule):
    id = "allowed_compartment_values"
    name = "Allowed compartment values"
    description = "Compartment must be SF or blood."
    severity = Severity.ERROR

    def validate(self, context: ValidationContext) -> ValidationResult:
        normalized = context.df["compartment"].map(
            lambda value: normalize_compartment(str(value))
        )
        invalid = context.df.loc[normalized.isna(), "compartment"].unique().tolist()
        count = int(normalized.isna().sum())
        if count:
            return _result(
                self,
                passed=False,
                message=f"Unsupported compartment values: {invalid}",
                details={"invalid_values": [str(v) for v in invalid]},
                affected_rows=count,
            )
        return _result(self, passed=True, message="All compartment values are supported.")


class AllowedChainValuesRule(ValidationRule):
    id = "allowed_chain_values"
    name = "Allowed chain values"
    description = "Chain must be one of the supported receptor chains."
    severity = Severity.WARNING

    def validate(self, context: ValidationContext) -> ValidationResult:
        chains = set(context.df["chain"].dropna().astype(str))
        unexpected = sorted(chains - ALLOWED_CHAINS)
        if unexpected:
            count = int(context.df["chain"].astype(str).isin(unexpected).sum())
            return _result(
                self,
                passed=False,
                message=f"Unexpected chain values: {unexpected}",
                details={"unexpected_chains": unexpected},
                affected_rows=count,
            )
        return _result(self, passed=True, message="All chain values are recognized.")


class DuplicateBarcodesRule(ValidationRule):
    id = "duplicate_barcodes"
    name = "Duplicate barcodes"
    description = "Report duplicate barcode counts per source file."
    severity = Severity.WARNING

    def validate(self, context: ValidationContext) -> ValidationResult:
        duplicates = context.df.duplicated(
            subset=["source_file", "barcode", "chain"], keep=False
        )
        count = int(duplicates.sum())
        return _result(
            self,
            passed=count == 0,
            message=f"Found {count} duplicate barcode-chain rows.",
            details={"duplicate_rows": count},
            affected_rows=count,
        )


class DuplicateContigsRule(ValidationRule):
    id = "duplicate_contigs"
    name = "Duplicate contigs"
    description = "Report duplicate contig_id values."
    severity = Severity.WARNING

    def validate(self, context: ValidationContext) -> ValidationResult:
        duplicates = context.df.duplicated(subset=["contig_id"], keep=False)
        count = int(duplicates.sum())
        return _result(
            self,
            passed=count == 0,
            message=f"Found {count} duplicate contig_id rows.",
            affected_rows=count,
        )


class MissingCdr3ProductiveRule(ValidationRule):
    id = "missing_cdr3_productive"
    name = "Missing CDR3 in productive contigs"
    description = "Productive receptors must have CDR3."
    severity = Severity.ERROR

    def validate(self, context: ValidationContext) -> ValidationResult:
        productive = context.df["productive"].fillna(False).astype(bool)
        empty_cdr3 = context.df["cdr3"].isna() | (
            context.df["cdr3"].astype(str) == "None"
        )
        mask = productive & empty_cdr3
        count = int(mask.sum())
        if count:
            return _result(
                self,
                passed=False,
                message=f"{count} productive rows have empty CDR3.",
                affected_rows=count,
            )
        return _result(self, passed=True, message="Productive rows have CDR3.")


class UmisPositiveRule(ValidationRule):
    id = "umis_positive"
    name = "UMIs non-negative"
    description = "UMI counts must be >= 0."
    severity = Severity.ERROR

    def validate(self, context: ValidationContext) -> ValidationResult:
        invalid = context.df["umis"] < 0
        count = int(invalid.sum())
        if count:
            return _result(
                self,
                passed=False,
                message=f"{count} rows have negative UMI counts.",
                affected_rows=count,
            )
        return _result(self, passed=True, message="All UMI counts are non-negative.")


class ReadsPositiveRule(ValidationRule):
    id = "reads_positive"
    name = "Reads non-negative"
    description = "Read counts must be >= 0."
    severity = Severity.ERROR

    def validate(self, context: ValidationContext) -> ValidationResult:
        invalid = context.df["reads"] < 0
        count = int(invalid.sum())
        if count:
            return _result(
                self,
                passed=False,
                message=f"{count} rows have negative read counts.",
                affected_rows=count,
            )
        return _result(self, passed=True, message="All read counts are non-negative.")


class PatientCompartmentBalanceRule(ValidationRule):
    id = "patient_compartment_balance"
    name = "Patient compartment balance"
    description = "Each patient should have both SF and blood compartments."
    severity = Severity.WARNING

    def validate(self, context: ValidationContext) -> ValidationResult:
        df = context.df.copy()
        df["compartment_norm"] = df["compartment"].map(
            lambda value: normalize_compartment(str(value))
        )
        missing_patients: list[str] = []
        for patient, group in df.groupby("patient"):
            compartments = set(group["compartment_norm"].dropna())
            if "SF" not in compartments or "blood" not in compartments:
                missing_patients.append(str(patient))
        if missing_patients:
            return _result(
                self,
                passed=False,
                message=(
                    f"{len(missing_patients)} patients are missing SF or blood "
                    "compartment coverage."
                ),
                details={"patients": missing_patients},
                affected_rows=len(missing_patients),
            )
        return _result(
            self,
            passed=True,
            message="All patients have SF and blood compartments.",
        )


class CellTypeDistributionRule(ValidationRule):
    id = "cell_type_distribution"
    name = "Cell type distribution"
    description = "Summarize CD4, CD8, Treg, and Unknown cell type counts."
    severity = Severity.INFO

    def validate(self, context: ValidationContext) -> ValidationResult:
        counts = context.df["cell_type"].astype(str).value_counts().to_dict()
        labeled = {
            label: int(counts.get(label, 0))
            for label in sorted(KNOWN_CELL_TYPES | set(counts.keys()))
        }
        return _result(
            self,
            passed=True,
            message="Cell type distribution computed.",
            details={"cell_type_counts": labeled},
        )


class SampleGroupUniquenessRule(ValidationRule):
    id = "sample_group_uniqueness"
    name = "Sample group uniqueness"
    description = "Each sample_group should map to one patient and compartment."
    severity = Severity.WARNING

    def validate(self, context: ValidationContext) -> ValidationResult:
        grouped = context.df.groupby("sample_group").agg(
            patients=("patient", "nunique"),
            compartments=("compartment", "nunique"),
        )
        conflicts = grouped[(grouped["patients"] > 1) | (grouped["compartments"] > 1)]
        count = int(len(conflicts))
        if count:
            return _result(
                self,
                passed=False,
                message=f"{count} sample_group values map to multiple patients/compartments.",
                details={"conflicting_sample_groups": conflicts.index.tolist()},
                affected_rows=count,
            )
        return _result(self, passed=True, message="Sample groups are consistent.")


class AdapterSchemaVersionRule(ValidationRule):
    id = "adapter_schema_version"
    name = "Adapter schema version"
    description = "Adapter version in data must match the registered adapter."
    severity = Severity.ERROR

    def validate(self, context: ValidationContext) -> ValidationResult:
        if "adapter_version" not in context.df.columns:
            return _result(
                self,
                passed=False,
                message="adapter_version column is missing.",
            )
        versions = set(context.df["adapter_version"].dropna().astype(str))
        if context.adapter_version not in versions:
            return _result(
                self,
                passed=False,
                message=(
                    f"Expected adapter version {context.adapter_version}, "
                    f"found {sorted(versions)}."
                ),
                details={"expected": context.adapter_version, "found": sorted(versions)},
            )
        return _result(self, passed=True, message="Adapter version is compatible.")


class HighConfidenceFractionRule(ValidationRule):
    id = "high_confidence_fraction"
    name = "High confidence fraction"
    description = "Report the fraction of high-confidence contigs."
    severity = Severity.INFO

    def validate(self, context: ValidationContext) -> ValidationResult:
        fraction = float(context.df["high_confidence"].fillna(False).astype(bool).mean())
        return _result(
            self,
            passed=True,
            message=f"High-confidence fraction: {fraction:.1%}",
            details={"high_confidence_fraction": round(fraction, 4)},
        )


def default_rules() -> list[ValidationRule]:
    """Return all built-in validation rules in execution order."""
    return [
        RequiredColumnsRule(),
        MissingPatientRule(),
        MissingCompartmentRule(),
        AllowedCompartmentValuesRule(),
        AllowedChainValuesRule(),
        DuplicateBarcodesRule(),
        DuplicateContigsRule(),
        MissingCdr3ProductiveRule(),
        UmisPositiveRule(),
        ReadsPositiveRule(),
        PatientCompartmentBalanceRule(),
        CellTypeDistributionRule(),
        SampleGroupUniquenessRule(),
        AdapterSchemaVersionRule(),
        HighConfidenceFractionRule(),
    ]
