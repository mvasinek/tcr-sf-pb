"""Validation helpers for unified adapter output."""

from __future__ import annotations

import pandas as pd

from tcr_bcr_tools.adapters.base import AdapterValidationResult
from tcr_bcr_tools.adapters.schema import REQUIRED_COLUMNS, SUPPORTED_CHAINS, SUPPORTED_COMPARTMENTS
from tcr_bcr_tools.build_detection_table import normalize_compartment


def validate_unified_schema(df: pd.DataFrame) -> AdapterValidationResult:
    """Validate a unified annotation table."""
    errors: list[str] = []
    warnings: list[str] = []

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")

    if not errors and df.empty:
        warnings.append("Unified table is empty.")

    if not errors and not df.empty:
        if df["patient"].astype(str).str.strip().eq("").any():
            errors.append("Column 'patient' contains empty values.")

        normalized_compartments = df["compartment"].map(
            lambda value: normalize_compartment(str(value))
        )
        unsupported = df.loc[normalized_compartments.isna(), "compartment"].unique()
        if len(unsupported):
            errors.append(
                "Unsupported compartment values: "
                + ", ".join(str(value) for value in unsupported)
            )

        unexpected_chains = sorted(
            set(df["chain"].dropna().astype(str))
            - SUPPORTED_CHAINS
            - {""}
        )
        if unexpected_chains:
            warnings.append(
                "Unexpected chain values: " + ", ".join(unexpected_chains)
            )

        non_productive = ~df["productive"].fillna(False).astype(bool)
        empty_cdr3 = df["cdr3"].isna() | (df["cdr3"].astype(str) == "None")
        invalid_cdr3 = empty_cdr3 & ~non_productive
        if invalid_cdr3.any():
            errors.append(
                "Column 'cdr3' is empty for productive contigs "
                f"({int(invalid_cdr3.sum())} rows)."
            )

    summary = {
        "n_rows": int(len(df)),
        "columns": list(df.columns),
        "supported_compartments": sorted(SUPPORTED_COMPARTMENTS),
    }
    return AdapterValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        detected_files=[],
        summary=summary,
    )
