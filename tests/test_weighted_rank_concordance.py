"""Tests for weighted Spearman rank concordance."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tcr_bcr_tools.weighted_rank_concordance import (
    WEIGHTED_SUMMARY_COLUMNS,
    compute_clone_weights,
    run_weighted_rank_concordance,
    summarize_weighted_rank_correlation,
    weighted_pearson_correlation,
    weighted_spearman_correlation,
)


def _rank_row(
    clonotype_key: str,
    *,
    blood_fraction: float,
    sf_fraction: float,
    blood_rank: int,
    sf_rank: int,
    patient: str = "p1",
    cell_type: str = "CD4",
) -> dict:
    n = 3
    return {
        "patient": patient,
        "cell_type": cell_type,
        "clonotype_key": clonotype_key,
        "blood_cells": int(blood_fraction * 100),
        "sf_cells": int(sf_fraction * 100),
        "blood_fraction": blood_fraction,
        "sf_fraction": sf_fraction,
        "blood_rank": blood_rank,
        "sf_rank": sf_rank,
        "blood_percentile": (n - blood_rank + 1) / n,
        "sf_percentile": (n - sf_rank + 1) / n,
    }


@pytest.fixture
def rank_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _rank_row("clone_a", blood_fraction=0.30, sf_fraction=0.30, blood_rank=1, sf_rank=1),
            _rank_row("clone_b", blood_fraction=0.20, sf_fraction=0.20, blood_rank=2, sf_rank=2),
            _rank_row("clone_c", blood_fraction=0.10, sf_fraction=0.10, blood_rank=3, sf_rank=3),
        ]
    )


def test_compute_weights_mean_fraction(rank_df: pd.DataFrame) -> None:
    weights = compute_clone_weights(rank_df, method="mean_fraction")
    assert weights.iloc[0] == pytest.approx(0.30)


def test_compute_weights_max_fraction(rank_df: pd.DataFrame) -> None:
    weights = compute_clone_weights(rank_df, method="max_fraction")
    assert weights.iloc[0] == pytest.approx(0.30)


def test_compute_weights_source_blood_fraction(rank_df: pd.DataFrame) -> None:
    weights = compute_clone_weights(rank_df, method="source_blood_fraction")
    assert weights.iloc[0] == pytest.approx(0.30)
    assert weights.iloc[2] == pytest.approx(0.10)


def test_weighted_pearson_positive() -> None:
    x = pd.Series([1.0, 2.0, 3.0])
    y = pd.Series([2.0, 4.0, 6.0])
    weights = pd.Series([1.0, 1.0, 1.0])
    assert weighted_pearson_correlation(x, y, weights) == pytest.approx(1.0)


def test_weighted_pearson_negative() -> None:
    x = pd.Series([1.0, 2.0, 3.0])
    y = pd.Series([9.0, 6.0, 3.0])
    weights = pd.Series([1.0, 1.0, 1.0])
    assert weighted_pearson_correlation(x, y, weights) == pytest.approx(-1.0)


def test_weighted_spearman_same_order(rank_df: pd.DataFrame) -> None:
    weights = compute_clone_weights(rank_df, method="max_fraction")
    value = weighted_spearman_correlation(
        rank_df["blood_fraction"], rank_df["sf_fraction"], weights
    )
    assert value == pytest.approx(1.0)


def test_weighted_spearman_opposite_order() -> None:
    df = pd.DataFrame(
        [
            _rank_row("clone_a", blood_fraction=0.30, sf_fraction=0.10, blood_rank=1, sf_rank=3),
            _rank_row("clone_b", blood_fraction=0.20, sf_fraction=0.20, blood_rank=2, sf_rank=2),
            _rank_row("clone_c", blood_fraction=0.10, sf_fraction=0.30, blood_rank=3, sf_rank=1),
        ]
    )
    weights = compute_clone_weights(df, method="max_fraction")
    value = weighted_spearman_correlation(
        df["blood_fraction"], df["sf_fraction"], weights
    )
    assert value == pytest.approx(-1.0)


def test_weighted_correlation_zero_weights() -> None:
    x = pd.Series([0.1, 0.2, 0.3])
    y = pd.Series([0.1, 0.2, 0.3])
    weights = pd.Series([0.0, 0.0, 0.0])
    assert np.isnan(weighted_pearson_correlation(x, y, weights))


def test_weighted_correlation_too_few_clones() -> None:
    x = pd.Series([0.1, 0.2])
    y = pd.Series([0.2, 0.1])
    weights = pd.Series([1.0, 1.0])
    assert np.isnan(weighted_spearman_correlation(x, y, weights))


def test_summarize_weighted_rank_correlation(rank_df: pd.DataFrame) -> None:
    summary = summarize_weighted_rank_correlation(rank_df, weight_method="max_fraction")
    patient_row = summary.loc[summary["patient"] == "p1"].iloc[0]
    all_row = summary.loc[summary["patient"] == "ALL"].iloc[0]

    assert list(summary.columns) == WEIGHTED_SUMMARY_COLUMNS
    assert patient_row["weighted_spearman_fraction"] == pytest.approx(1.0)
    assert patient_row["weighted_spearman_rank"] == pytest.approx(1.0)
    assert all_row["n_clones"] == 3


def test_filter_cell_type(rank_df: pd.DataFrame) -> None:
    extended = pd.concat(
        [
            rank_df,
            pd.DataFrame(
                [
                    _rank_row(
                        "clone_d",
                        blood_fraction=0.40,
                        sf_fraction=0.35,
                        blood_rank=1,
                        sf_rank=1,
                        cell_type="CD8",
                    ),
                    _rank_row(
                        "clone_e",
                        blood_fraction=0.25,
                        sf_fraction=0.20,
                        blood_rank=2,
                        sf_rank=2,
                        cell_type="CD8",
                    ),
                    _rank_row(
                        "clone_f",
                        blood_fraction=0.10,
                        sf_fraction=0.05,
                        blood_rank=3,
                        sf_rank=3,
                        cell_type="CD8",
                    ),
                ]
            ),
        ],
        ignore_index=True,
    )
    summary = summarize_weighted_rank_correlation(
        extended.loc[extended["cell_type"] == "CD8"],
        weight_method="max_fraction",
    )
    assert set(summary["cell_type"]) == {"CD8"}


def test_run_weighted_rank_concordance_no_plots(
    rank_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "rank_table.csv"
    output_dir = tmp_path / "outputs"
    rank_df.to_csv(input_path, index=False)

    run_weighted_rank_concordance(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=False,
    )

    out_dir = output_dir / "weighted_rank_concordance"
    assert (out_dir / "weighted_rank_correlation_summary.csv").exists()
    assert not (out_dir / "weighted_spearman_by_cell_type.png").exists()


def test_run_weighted_rank_concordance_creates_plots(
    rank_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "rank_table.csv"
    output_dir = tmp_path / "outputs_plots"
    rank_df.to_csv(input_path, index=False)

    run_weighted_rank_concordance(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=True,
    )

    out_dir = output_dir / "weighted_rank_concordance"
    assert (out_dir / "weighted_spearman_by_cell_type.png").exists()
    assert (out_dir / "clone_weight_distribution.png").exists()
