"""Tests for decile information analysis."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tcr_bcr_tools.decile_information import (
    DECILE_TABLE_COLUMNS,
    INFORMATION_METRICS_COLUMNS,
    TOP_DECILE_ENRICHMENT_COLUMNS,
    TRANSITION_MATRIX_COLUMNS,
    assign_compartment_bins,
    build_transition_matrix,
    compute_information_metrics,
    compute_top_bin_enrichment,
    entropy_from_labels,
    run_decile_information_analysis,
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
    rows = []
    for index in range(10):
        fraction = (10 - index) / 100.0
        rows.append(
            _detection_row(
                f"clone_{index}",
                sf_cells=10 - index,
                blood_cells=10 - index,
                sf_fraction=fraction,
                blood_fraction=fraction,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            )
        )
    rows.extend(
        [
            _detection_row(
                "tie_fraction_a",
                sf_cells=5,
                blood_cells=8,
                sf_fraction=0.05,
                blood_fraction=0.05,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "tie_fraction_b",
                sf_cells=3,
                blood_cells=3,
                sf_fraction=0.05,
                blood_fraction=0.05,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "cd8_clone",
                sf_cells=4,
                blood_cells=4,
                sf_fraction=0.04,
                blood_fraction=0.04,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
            _detection_row(
                "cd8_clone_b",
                sf_cells=2,
                blood_cells=2,
                sf_fraction=0.02,
                blood_fraction=0.02,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
            _detection_row(
                "cd8_clone_c",
                sf_cells=1,
                blood_cells=1,
                sf_fraction=0.01,
                blood_fraction=0.01,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
        ]
    )
    return pd.DataFrame(rows)


def test_assign_blood_bin(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    assert binned["blood_decile"].notna().all()


def test_assign_sf_bin(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    assert binned["sf_decile"].notna().all()


def test_largest_clone_gets_bin_10(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    largest = binned.loc[binned["clonotype_key"] == "clone_0"].iloc[0]
    assert largest["blood_decile"] == 10
    assert largest["sf_decile"] == 10


def test_smallest_clone_gets_bin_1(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    smallest = binned.loc[binned["clonotype_key"] == "clone_9"].iloc[0]
    assert smallest["blood_decile"] == 1
    assert smallest["sf_decile"] == 1


def test_tie_breaking_by_cells(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    tie_a = binned.loc[binned["clonotype_key"] == "tie_fraction_a"].iloc[0]
    tie_b = binned.loc[binned["clonotype_key"] == "tie_fraction_b"].iloc[0]
    assert tie_a["blood_decile"] > tie_b["blood_decile"]


def test_transition_matrix_all_combinations(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    matrix = build_transition_matrix(binned, n_bins=10)
    cd4 = matrix.loc[matrix["cell_type"] == "CD4"]
    assert len(cd4) == 100
    assert list(matrix.columns) == TRANSITION_MATRIX_COLUMNS


def test_fraction_of_blood_decile(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    matrix = build_transition_matrix(binned, n_bins=10)
    blood_decile_10 = matrix.loc[
        (matrix["cell_type"] == "CD4") & (matrix["blood_decile"] == 10)
    ]
    row_sum = blood_decile_10["fraction_of_blood_decile"].sum()
    assert row_sum == pytest.approx(1.0)


def test_fraction_of_all_clones(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    matrix = build_transition_matrix(binned, n_bins=10)
    cd4 = matrix.loc[matrix["cell_type"] == "CD4"]
    assert cd4["fraction_of_all_clones"].sum() == pytest.approx(1.0)


def test_entropy_constant_labels() -> None:
    assert entropy_from_labels(pd.Series([1, 1, 1])) == pytest.approx(0.0)


def test_entropy_uniform_labels() -> None:
    labels = pd.Series([1, 2, 3, 4])
    assert entropy_from_labels(labels) == pytest.approx(2.0)


def test_mutual_information_identical_deciles() -> None:
    binned = pd.DataFrame(
        {
            "cell_type": ["CD4"] * 4,
            "blood_decile": [1, 2, 3, 4],
            "sf_decile": [1, 2, 3, 4],
        }
    )
    metrics = compute_information_metrics(binned)
    assert metrics.iloc[0]["mutual_information"] > 0.5


def test_mutual_information_independent_deciles() -> None:
    binned = pd.DataFrame(
        {
            "cell_type": ["CD4"] * 8,
            "blood_decile": [1, 1, 1, 1, 2, 2, 2, 2],
            "sf_decile": [1, 2, 3, 4, 1, 2, 3, 4],
        }
    )
    metrics = compute_information_metrics(binned)
    assert metrics.iloc[0]["mutual_information"] == pytest.approx(0.0, abs=1e-9)


def test_normalized_mutual_information(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    metrics = compute_information_metrics(binned)
    cd4 = metrics.loc[metrics["cell_type"] == "CD4"].iloc[0]
    assert 0.0 <= cd4["normalized_mutual_information"] <= 1.0


def test_uncertainty_reduction(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    metrics = compute_information_metrics(binned)
    cd4 = metrics.loc[metrics["cell_type"] == "CD4"].iloc[0]
    assert cd4["uncertainty_reduction_sf_given_blood"] > 0.0


def test_top_decile_enrichment(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    enrichment = compute_top_bin_enrichment(binned, n_bins=10)
    cd4 = enrichment.loc[enrichment["cell_type"] == "CD4"].iloc[0]
    assert cd4["n_both_top"] >= 1
    assert cd4["enrichment_vs_random"] > 1.0


def test_odds_ratio_haldane_correction() -> None:
    binned = pd.DataFrame(
        {
            "cell_type": ["CD4"] * 4,
            "blood_decile": [10, 10, 1, 1],
            "sf_decile": [10, 1, 10, 1],
        }
    )
    enrichment = compute_top_bin_enrichment(binned, n_bins=10)
    assert enrichment.iloc[0]["odds_ratio"] > 0.0


def test_filter_cell_type(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(
        detection_df.loc[detection_df["cell_type"] == "CD8"], n_bins=10
    )
    assert set(binned["cell_type"]) == {"CD8"}


def test_n_bins_parameter() -> None:
    df = pd.DataFrame(
        [
            _detection_row("a", sf_fraction=0.3, blood_fraction=0.3, sf_cells=3, blood_cells=3),
            _detection_row("b", sf_fraction=0.2, blood_fraction=0.2, sf_cells=2, blood_cells=2),
            _detection_row("c", sf_fraction=0.1, blood_fraction=0.1, sf_cells=1, blood_cells=1),
        ]
    )
    binned = assign_compartment_bins(df, n_bins=3)
    assert set(binned["blood_decile"]).issubset({1, 2, 3})


def test_run_no_plots(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs"
    detection_df.to_csv(input_path, index=False)

    run_decile_information_analysis(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=False,
    )

    out_dir = output_dir / "decile_information"
    assert (out_dir / "decile_table.csv").exists()
    assert (out_dir / "decile_transition_matrix.csv").exists()
    assert (out_dir / "information_metrics_summary.csv").exists()
    assert (out_dir / "top_decile_enrichment.csv").exists()
    assert not (out_dir / "decile_heatmap_counts.png").exists()


def test_run_creates_heatmap_plots(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs_plots"
    detection_df.to_csv(input_path, index=False)

    run_decile_information_analysis(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=True,
    )

    out_dir = output_dir / "decile_information"
    assert (out_dir / "decile_heatmap_counts.png").exists()
    assert (out_dir / "decile_heatmap_row_fraction.png").exists()
    assert (out_dir / "information_metrics_by_cell_type.png").exists()
    assert (out_dir / "top_decile_enrichment.png").exists()


def test_decile_table_columns(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    assert list(binned.columns) == DECILE_TABLE_COLUMNS


def test_information_metrics_columns(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    metrics = compute_information_metrics(binned)
    assert list(metrics.columns) == INFORMATION_METRICS_COLUMNS


def test_top_enrichment_columns(detection_df: pd.DataFrame) -> None:
    binned = assign_compartment_bins(detection_df, n_bins=10)
    enrichment = compute_top_bin_enrichment(binned, n_bins=10)
    assert list(enrichment.columns) == TOP_DECILE_ENRICHMENT_COLUMNS
