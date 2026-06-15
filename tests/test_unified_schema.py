"""Tests for unified annotation schema validation."""

import pandas as pd

from tcr_bcr_tools.adapters.schema import REQUIRED_COLUMNS
from tcr_bcr_tools.adapters.validation import validate_unified_schema


def _valid_row(**overrides) -> dict:
    row = {
        "dataset_id": "GSE160097",
        "source_file": "sample.csv.gz",
        "sample_id": "GSM1",
        "patient": "p1",
        "sample_group": "PM1",
        "compartment": "SF",
        "cell_type": "CD4",
        "barcode": "CELL-1",
        "contig_id": "c1",
        "chain": "TRA",
        "v_gene": "TRAV1",
        "d_gene": None,
        "j_gene": "TRAJ1",
        "c_gene": "TRAC",
        "cdr3": "CAVSDYGQNFVF",
        "cdr3_nt": "AAA",
        "productive": True,
        "full_length": True,
        "high_confidence": True,
        "is_cell": True,
        "umis": 3,
        "reads": 10,
        "raw_clonotype_id": "clonotype1",
        "raw_consensus_id": "consensus1",
        "adapter_name": "tenx",
        "adapter_version": "0.5.3",
    }
    row.update(overrides)
    return row


def test_validate_unified_schema_passes() -> None:
    df = pd.DataFrame([_valid_row(), _valid_row(barcode="CELL-2", compartment="blood")])
    result = validate_unified_schema(df)
    assert result.valid is True


def test_validate_unified_schema_missing_column_fails() -> None:
    df = pd.DataFrame([_valid_row()])
    df = df.drop(columns=["patient"])
    result = validate_unified_schema(df)
    assert result.valid is False
    assert any("patient" in error for error in result.errors)


def test_validate_unified_schema_empty_patient_fails() -> None:
    df = pd.DataFrame([_valid_row(patient="")])
    result = validate_unified_schema(df)
    assert result.valid is False


def test_validate_unified_schema_productive_requires_cdr3() -> None:
    df = pd.DataFrame([_valid_row(cdr3=None, productive=True)])
    result = validate_unified_schema(df)
    assert result.valid is False


def test_required_columns_list() -> None:
    assert "dataset_id" in REQUIRED_COLUMNS
    assert "adapter_version" in REQUIRED_COLUMNS
