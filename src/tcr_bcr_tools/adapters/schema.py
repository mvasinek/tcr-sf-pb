"""Unified annotation schema for adapter output."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "dataset_id",
    "source_file",
    "sample_id",
    "patient",
    "sample_group",
    "compartment",
    "cell_type",
    "barcode",
    "contig_id",
    "chain",
    "v_gene",
    "d_gene",
    "j_gene",
    "c_gene",
    "cdr3",
    "cdr3_nt",
    "productive",
    "full_length",
    "high_confidence",
    "is_cell",
    "umis",
    "reads",
    "raw_clonotype_id",
    "raw_consensus_id",
    "adapter_name",
    "adapter_version",
]

OPTIONAL_COLUMNS = [
    "platform",
    "study_id",
    "disease",
    "tissue",
    "timepoint",
    "condition",
    "batch",
    "library_id",
]

SUPPORTED_COMPARTMENTS = {"SF", "blood"}
SUPPORTED_CHAINS = {"TRA", "TRB", "Multi", "IGK", "IGL", "IGH"}

UNIFIED_ANNOTATIONS_FILE = "unified_annotations.csv"
ADAPTER_REPORT_FILE = "adapter_report.yaml"


def ensure_legacy_annotation_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map unified annotation columns to legacy analysis column names."""
    result = df.copy()
    if "gsm_id" not in result.columns and "sample_id" in result.columns:
        result["gsm_id"] = result["sample_id"]
    if "length" not in result.columns:
        result["length"] = pd.NA
    return result
