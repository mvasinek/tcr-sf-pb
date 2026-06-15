"""Tests for expansion threshold sweep analysis."""

from pathlib import Path

import pandas as pd
import pytest

from tcr_bcr_tools.expansion_concordance import CONCORDANCE_SUMMARY_COLUMNS
from tcr_bcr_tools.threshold_sweep import (
    SWEEP_PATIENT_COLUMNS,
    get_default_thresholds,
    parse_thresholds,
    plot_expanded_counts_by_threshold,
    plot_threshold_sweep_curves,
    plot_threshold_sweep_jaccard,
    run_threshold_sweep,
    run_threshold_sweep_cli,
)


def _detection_row(
    clonotype_key: str,
    *,
    sf_cells: int = 0,
    blood_cells: int = 0,
    sf_fraction: float = 0.0,
    blood_fraction: float = 0.0,
    detected_in_sf: bool = False,
    detected_in_blood: bool = False,
    shared_clone: bool = False,
    patient: str = "p1",
    cell_type: str = "CD4",
) -> dict:
    return {
        "patient": patient,
        "cell_type": cell_type,
        "clonotype_key": clonotype_key,
        "sf_cells": sf_cells,
        "blood_cells": blood_cells,
        "sf_fraction": sf_fraction,
        "blood_fraction": blood_fraction,
        "detected_in_sf": detected_in_sf,
        "detected_in_blood": detected_in_blood,
        "shared_clone": shared_clone,
    }


@pytest.fixture
def detection_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _detection_row(
                "clone_both",
                sf_cells=10,
                blood_cells=8,
                sf_fraction=0.01,
                blood_fraction=0.008,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "clone_sf_only",
                sf_cells=6,
                blood_cells=0,
                sf_fraction=0.006,
                blood_fraction=0.0,
                detected_in_sf=True,
            ),
            _detection_row(
                "clone_blood_only",
                sf_cells=0,
                blood_cells=7,
                blood_fraction=0.007,
                detected_in_blood=True,
            ),
            _detection_row(
                "clone_none",
                sf_cells=1,
                blood_cells=1,
                sf_fraction=0.001,
                blood_fraction=0.001,
                detected_in_sf=True,
                detected_in_blood=True,
            ),
            _detection_row(
                "clone_cd8",
                sf_cells=12,
                blood_cells=4,
                sf_fraction=0.02,
                blood_fraction=0.004,
                detected_in_sf=True,
                detected_in_blood=True,
                cell_type="CD8",
            ),
        ]
    )


def test_default_thresholds_fraction() -> None:
    assert get_default_thresholds("fraction") == [
        0.0005, 0.001, 0.002, 0.003, 0.005, 0.0075, 0.01, 0.02, 0.05,
    ]


def test_default_thresholds_cells() -> None:
    assert get_default_thresholds("cells") == [2, 3, 5, 10, 20, 50, 100]


def test_default_thresholds_quantile() -> None:
    assert get_default_thresholds("quantile") == [0.80, 0.85, 0.90, 0.95, 0.975, 0.99]


def test_parse_thresholds_custom() -> None:
    assert parse_thresholds("0.001,0.002,0.005", "fraction") == [0.001, 0.002, 0.005]


def test_parse_thresholds_defaults_when_none() -> None:
    assert parse_thresholds(None, "cells") == [2, 3, 5, 10, 20, 50, 100]


def test_invalid_method_rejected() -> None:
    with pytest.raises(ValueError):
        get_default_thresholds("invalid")
    with pytest.raises(ValueError):
        run_threshold_sweep(pd.DataFrame(), method="invalid")


def test_sweep_two_thresholds(detection_df: pd.DataFrame) -> None:
    summary, patient_summary = run_threshold_sweep(
        detection_df.loc[detection_df["cell_type"] == "CD4"],
        method="fraction",
        thresholds=[0.005, 0.01],
    )
    assert len(summary) == 2
    assert list(summary.columns) == CONCORDANCE_SUMMARY_COLUMNS
    assert summary["expansion_threshold"].tolist() == [0.005, 0.01]
    assert len(patient_summary) == 2
    assert list(patient_summary.columns) == SWEEP_PATIENT_COLUMNS


def test_filter_cell_type(detection_df: pd.DataFrame) -> None:
    summary, patient_summary = run_threshold_sweep(
        detection_df,
        method="fraction",
        thresholds=[0.005],
        cell_type="CD8",
    )
    assert len(summary) == 1
    assert summary.iloc[0]["cell_type"] == "CD8"
    assert len(patient_summary) == 1


def test_run_threshold_sweep_cli_no_plots(
    detection_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs"
    detection_df.to_csv(input_path, index=False)

    run_threshold_sweep_cli(
        input_path=input_path,
        output_dir=output_dir,
        method="fraction",
        thresholds=[0.005, 0.01],
        make_plots=False,
    )

    sweep_dir = output_dir / "threshold_sweep"
    assert (sweep_dir / "threshold_sweep_summary.csv").exists()
    assert (sweep_dir / "threshold_sweep_by_patient.csv").exists()
    assert not (sweep_dir / "threshold_sweep_curves.png").exists()


def test_run_threshold_sweep_cli_creates_plots(
    detection_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs_plots"
    detection_df.to_csv(input_path, index=False)

    run_threshold_sweep_cli(
        input_path=input_path,
        output_dir=output_dir,
        method="fraction",
        thresholds=[0.005, 0.01],
        make_plots=True,
    )

    sweep_dir = output_dir / "threshold_sweep"
    assert (sweep_dir / "threshold_sweep_curves.png").exists()
    assert (sweep_dir / "threshold_sweep_jaccard.png").exists()
    assert (sweep_dir / "threshold_sweep_expanded_counts.png").exists()


def test_plot_functions_create_png(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    summary, _ = run_threshold_sweep(
        detection_df,
        method="fraction",
        thresholds=[0.005, 0.01],
    )
    plot_threshold_sweep_curves(summary, tmp_path / "curves.png")
    plot_threshold_sweep_jaccard(summary, tmp_path / "jaccard.png")
    plot_expanded_counts_by_threshold(summary, tmp_path / "counts.png")
    assert (tmp_path / "curves.png").exists()
    assert (tmp_path / "jaccard.png").exists()
    assert (tmp_path / "counts.png").exists()
