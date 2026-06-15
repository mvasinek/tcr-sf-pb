"""Tests for validation rules."""

from pathlib import Path

import pandas as pd
import pytest

from tcr_bcr_tools.adapters.schema import REQUIRED_COLUMNS
from tcr_bcr_tools.validation.rules import (
    AllowedCompartmentValuesRule,
    MissingPatientRule,
    RequiredColumnsRule,
    ValidationContext,
    default_rules,
)
from tcr_bcr_tools.validation.severity import Severity
from tcr_bcr_tools.validation.summary import compute_summary


def _row(**overrides) -> dict:
    base = {
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
    base.update(overrides)
    return base


def _context(df: pd.DataFrame) -> ValidationContext:
    return ValidationContext(
        dataset_id="GSE160097",
        adapter="tenx",
        adapter_version="0.5.3",
        df=df,
    )


def test_default_rules_count() -> None:
    assert len(default_rules()) == 15


def test_required_columns_pass() -> None:
    df = pd.DataFrame([_row(), _row(barcode="CELL-2", compartment="blood")])
    result = RequiredColumnsRule().validate(_context(df))
    assert result.passed is True


def test_required_columns_fail() -> None:
    df = pd.DataFrame([_row()])
    df = df.drop(columns=["patient"])
    result = RequiredColumnsRule().validate(_context(df))
    assert result.passed is False
    assert result.severity == Severity.CRITICAL


def test_missing_patient_rule() -> None:
    df = pd.DataFrame([_row(patient="")])
    result = MissingPatientRule().validate(_context(df))
    assert result.passed is False
    assert result.severity == Severity.ERROR


def test_allowed_compartment_values() -> None:
    df = pd.DataFrame([_row(compartment="tissue")])
    result = AllowedCompartmentValuesRule().validate(_context(df))
    assert result.passed is False


def test_compute_summary_score() -> None:
    results = [
        RequiredColumnsRule().validate(_context(pd.DataFrame([_row()]))),
        MissingPatientRule().validate(_context(pd.DataFrame([_row(patient="")]))),
    ]
    summary = compute_summary(results)
    assert summary.failed >= 1
    assert 0 <= summary.score <= 100
