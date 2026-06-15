"""Tests for expansion concordance analysis."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tcr_bcr_tools.expansion_concordance import (
    CONCORDANCE_SUMMARY_COLUMNS,
    EXPANSION_STATUS_TABLE_COLUMNS,
    classify_expansion,
    plot_expansion_status_counts,
    plot_patient_concordance_matrix,
    plot_sf_vs_blood_fraction_scatter,
    run_expansion_concordance_analysis,
    summarize_expansion_concordance,
    summarize_expansion_concordance_by_patient,
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
                detected_in_blood=False,
            ),
            _detection_row(
                "clone_blood_only",
                sf_cells=0,
                blood_cells=7,
                sf_fraction=0.0,
                blood_fraction=0.007,
                detected_in_sf=False,
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
                shared_clone=True,
            ),
            _detection_row(
                "clone_cd8",
                sf_cells=12,
                blood_cells=4,
                sf_fraction=0.02,
                blood_fraction=0.004,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
        ]
    )


def test_fraction_expansion_definition(detection_df: pd.DataFrame) -> None:
    result = classify_expansion(detection_df, method="fraction", threshold=0.005)
    both = result.loc[result["clonotype_key"] == "clone_both"].iloc[0]
    none = result.loc[result["clonotype_key"] == "clone_none"].iloc[0]
    assert both["sf_expanded"] == True  # noqa: E712
    assert both["blood_expanded"] == True  # noqa: E712
    assert none["sf_expanded"] == False  # noqa: E712
    assert none["blood_expanded"] == False  # noqa: E712


def test_cells_expansion_definition(detection_df: pd.DataFrame) -> None:
    result = classify_expansion(detection_df, method="cells", threshold=5)
    sf_only = result.loc[result["clonotype_key"] == "clone_sf_only"].iloc[0]
    none = result.loc[result["clonotype_key"] == "clone_none"].iloc[0]
    assert sf_only["sf_expanded"] == True  # noqa: E712
    assert sf_only["blood_expanded"] == False  # noqa: E712
    assert none["sf_expanded"] == False  # noqa: E712


def test_quantile_expansion_definition() -> None:
    df = pd.DataFrame(
        [
            _detection_row("c1", sf_fraction=0.01, blood_fraction=0.01, detected_in_sf=True, detected_in_blood=True),
            _detection_row("c2", sf_fraction=0.02, blood_fraction=0.02, detected_in_sf=True, detected_in_blood=True),
            _detection_row("c3", sf_fraction=0.03, blood_fraction=0.03, detected_in_sf=True, detected_in_blood=True),
            _detection_row("c4", sf_fraction=0.04, blood_fraction=0.04, detected_in_sf=True, detected_in_blood=True),
            _detection_row("c5", sf_fraction=0.05, blood_fraction=0.05, detected_in_sf=True, detected_in_blood=True),
        ]
    )
    result = classify_expansion(df, method="quantile", threshold=0.8)
    assert result["sf_expanded"].sum() == 1
    assert result["blood_expanded"].sum() == 1
    assert result.loc[result["clonotype_key"] == "c5", "sf_expanded"].iloc[0] == True  # noqa: E712


def test_expansion_status_expanded_both(detection_df: pd.DataFrame) -> None:
    result = classify_expansion(detection_df, method="fraction", threshold=0.005)
    assert (
        result.loc[result["clonotype_key"] == "clone_both", "expansion_status"].iloc[0]
        == "expanded_both"
    )


def test_expansion_status_expanded_sf_only(detection_df: pd.DataFrame) -> None:
    result = classify_expansion(detection_df, method="fraction", threshold=0.005)
    assert (
        result.loc[result["clonotype_key"] == "clone_sf_only", "expansion_status"].iloc[0]
        == "expanded_sf_only"
    )


def test_expansion_status_expanded_blood_only(detection_df: pd.DataFrame) -> None:
    result = classify_expansion(detection_df, method="fraction", threshold=0.005)
    assert (
        result.loc[
            result["clonotype_key"] == "clone_blood_only", "expansion_status"
        ].iloc[0]
        == "expanded_blood_only"
    )


def test_expansion_status_not_expanded(detection_df: pd.DataFrame) -> None:
    result = classify_expansion(detection_df, method="fraction", threshold=0.005)
    assert (
        result.loc[result["clonotype_key"] == "clone_none", "expansion_status"].iloc[0]
        == "not_expanded"
    )


def test_concordance_probabilities(detection_df: pd.DataFrame) -> None:
    status = classify_expansion(
        detection_df.loc[detection_df["cell_type"] == "CD4"],
        method="fraction",
        threshold=0.005,
    )
    summary = summarize_expansion_concordance(status, method="fraction", threshold=0.005)
    row = summary.iloc[0]

    assert row["n_sf_expanded"] == 2
    assert row["n_blood_expanded"] == 2
    assert row["n_expanded_both"] == 1
    assert row["p_sf_expanded_given_blood_expanded"] == pytest.approx(0.5)
    assert row["p_blood_expanded_given_sf_expanded"] == pytest.approx(0.5)
    assert row["jaccard_expanded"] == pytest.approx(1 / 3)


def test_concordance_zero_denominator_returns_nan() -> None:
    df = classify_expansion(
        pd.DataFrame(
            [
                _detection_row(
                    "only_sf",
                    sf_fraction=0.01,
                    detected_in_sf=True,
                )
            ]
        ),
        method="fraction",
        threshold=0.005,
    )
    summary = summarize_expansion_concordance(df, method="fraction", threshold=0.005)
    row = summary.iloc[0]
    assert np.isnan(row["p_sf_expanded_given_blood_expanded"])
    assert row["p_blood_expanded_given_sf_expanded"] == pytest.approx(0.0)
    assert row["jaccard_expanded"] == pytest.approx(0.0)


def test_patient_level_summary(detection_df: pd.DataFrame) -> None:
    status = classify_expansion(detection_df, method="fraction", threshold=0.005)
    patient_summary = summarize_expansion_concordance_by_patient(
        status, method="fraction", threshold=0.005
    )
    cd4 = patient_summary.loc[patient_summary["cell_type"] == "CD4"].iloc[0]
    assert cd4["patient"] == "p1"
    assert cd4["n_clones"] == 4


def test_filter_cell_type(detection_df: pd.DataFrame) -> None:
    status = classify_expansion(
        detection_df.loc[detection_df["cell_type"] == "CD4"],
        method="fraction",
        threshold=0.005,
    )
    assert set(status["clonotype_key"]) == {
        "clone_both",
        "clone_sf_only",
        "clone_blood_only",
        "clone_none",
    }


def test_run_expansion_concordance_no_plots(
    detection_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs"
    detection_df.to_csv(input_path, index=False)

    run_expansion_concordance_analysis(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=False,
    )

    assert (output_dir / "expansion_status_table.csv").exists()
    assert (output_dir / "expansion_concordance_summary.csv").exists()
    assert (output_dir / "expansion_concordance_by_patient.csv").exists()
    assert not (output_dir / "expansion" / "expansion_status_counts.png").exists()


def test_run_expansion_concordance_creates_plots(
    detection_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs_plots"
    detection_df.to_csv(input_path, index=False)

    run_expansion_concordance_analysis(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=True,
    )

    expansion_dir = output_dir / "expansion"
    assert (expansion_dir / "expansion_status_counts.png").exists()
    assert (expansion_dir / "sf_vs_blood_fraction_scatter.png").exists()
    assert (expansion_dir / "patient_concordance_matrix.png").exists()

    status = pd.read_csv(output_dir / "expansion_status_table.csv")
    assert list(status.columns) == EXPANSION_STATUS_TABLE_COLUMNS
    summary = pd.read_csv(output_dir / "expansion_concordance_summary.csv")
    assert list(summary.columns) == CONCORDANCE_SUMMARY_COLUMNS


def test_plot_functions_create_png(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    status = classify_expansion(detection_df, method="fraction", threshold=0.005)
    patient_summary = summarize_expansion_concordance_by_patient(
        status, method="fraction", threshold=0.005
    )
    plot_expansion_status_counts(status, tmp_path / "status.png")
    plot_sf_vs_blood_fraction_scatter(status, tmp_path / "scatter.png")
    plot_patient_concordance_matrix(patient_summary, tmp_path / "matrix.png")
    assert (tmp_path / "status.png").exists()
    assert (tmp_path / "scatter.png").exists()
    assert (tmp_path / "matrix.png").exists()
