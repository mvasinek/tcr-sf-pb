"""Tests for rank and percentile concordance analysis."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tcr_bcr_tools.rank_concordance import (
    PERCENTILE_CONCORDANCE_COLUMNS,
    RANK_CORRELATION_COLUMNS,
    RANK_TABLE_COLUMNS,
    TOP_OVERLAP_COLUMNS,
    compute_clone_ranks,
    compute_percentile_concordance,
    compute_percentiles,
    compute_rank_correlations,
    compute_top_overlap,
    plot_percentile_heatmap,
    plot_rank_scatter,
    plot_top_overlap_curve,
    run_rank_concordance,
)


def _row(
    clonotype_key: str,
    *,
    sf_cells: int = 0,
    blood_cells: int = 0,
    sf_fraction: float = 0.0,
    blood_fraction: float = 0.0,
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
    }


@pytest.fixture
def detection_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _row("clone_a", sf_cells=10, blood_cells=8, sf_fraction=0.10, blood_fraction=0.08),
            _row("clone_b", sf_cells=6, blood_cells=6, sf_fraction=0.06, blood_fraction=0.06),
            _row("clone_c", sf_cells=4, blood_cells=2, sf_fraction=0.04, blood_fraction=0.02),
            _row(
                "clone_d",
                sf_cells=12,
                blood_cells=4,
                sf_fraction=0.02,
                blood_fraction=0.04,
                cell_type="CD8",
            ),
        ]
    )


def test_compute_clone_ranks(detection_df: pd.DataFrame) -> None:
    ranked = compute_clone_ranks(detection_df)
    cd4 = ranked.loc[ranked["cell_type"] == "CD4"]
    assert cd4.loc[cd4["clonotype_key"] == "clone_a", "blood_rank"].iloc[0] == 1
    assert cd4.loc[cd4["clonotype_key"] == "clone_c", "blood_rank"].iloc[0] == 3
    assert cd4.loc[cd4["clonotype_key"] == "clone_a", "sf_rank"].iloc[0] == 1
    assert cd4.loc[cd4["clonotype_key"] == "clone_c", "sf_rank"].iloc[0] == 3


def test_rank_tie_break_by_cells_then_key() -> None:
    df = pd.DataFrame(
        [
            _row("clone_z", sf_cells=5, blood_cells=5, sf_fraction=0.05, blood_fraction=0.05),
            _row("clone_a", sf_cells=3, blood_cells=3, sf_fraction=0.05, blood_fraction=0.05),
            _row("clone_m", sf_cells=7, blood_cells=7, sf_fraction=0.05, blood_fraction=0.05),
        ]
    )
    ranked = compute_clone_ranks(df)
    assert ranked.sort_values("blood_rank")["clonotype_key"].tolist() == [
        "clone_m",
        "clone_z",
        "clone_a",
    ]


def test_compute_percentiles(detection_df: pd.DataFrame) -> None:
    ranked = compute_clone_ranks(detection_df)
    table = compute_percentiles(ranked)
    cd4_top = table.loc[
        (table["cell_type"] == "CD4") & (table["clonotype_key"] == "clone_a")
    ].iloc[0]
    assert cd4_top["blood_percentile"] == pytest.approx(1.0)
    assert cd4_top["sf_percentile"] == pytest.approx(1.0)
    cd4_bottom = table.loc[
        (table["cell_type"] == "CD4") & (table["clonotype_key"] == "clone_c")
    ].iloc[0]
    assert cd4_bottom["blood_percentile"] == pytest.approx(1 / 3)
    assert list(table.columns) == RANK_TABLE_COLUMNS


def test_spearman_fraction_correlation(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    summary = compute_rank_correlations(table)
    cd4 = summary.loc[
        (summary["patient"] == "p1") & (summary["cell_type"] == "CD4")
    ].iloc[0]
    assert cd4["spearman_fraction"] == pytest.approx(1.0)


def test_pearson_fraction_correlation(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    summary = compute_rank_correlations(table)
    cd4 = summary.loc[
        (summary["patient"] == "p1") & (summary["cell_type"] == "CD4")
    ].iloc[0]
    assert cd4["pearson_fraction"] == pytest.approx(0.9285714285714286)


def test_kendall_fraction_correlation(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    summary = compute_rank_correlations(table)
    cd4 = summary.loc[
        (summary["patient"] == "p1") & (summary["cell_type"] == "CD4")
    ].iloc[0]
    assert cd4["kendall_fraction"] == pytest.approx(1.0)


def test_global_all_correlation_row(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    summary = compute_rank_correlations(table)
    assert "ALL" in set(summary["patient"])


def test_percentile_concordance(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    summary = compute_percentile_concordance(table)
    row = summary.loc[
        (summary["cell_type"] == "CD4") & (summary["percentile_threshold"] == 0.50)
    ].iloc[0]
    assert row["n_sf_top"] == 2
    assert row["n_blood_top"] == 2
    assert row["n_top_both"] == 2
    assert row["p_sf_top_given_blood_top"] == pytest.approx(1.0)
    assert list(summary.columns) == PERCENTILE_CONCORDANCE_COLUMNS


def test_top_overlap_top1(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    summary = compute_top_overlap(table)
    row = summary.loc[(summary["cell_type"] == "CD4") & (summary["top_n"] == 1)].iloc[0]
    assert row["blood_overlap"] == pytest.approx(1.0)
    assert row["sf_overlap"] == pytest.approx(1.0)


def test_top_overlap_top10(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    summary = compute_top_overlap(table)
    row = summary.loc[(summary["cell_type"] == "CD4") & (summary["top_n"] == 10)].iloc[0]
    assert row["blood_overlap"] == pytest.approx(1.0)
    assert row["sf_overlap"] == pytest.approx(1.0)


def test_top_overlap_top100(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    summary = compute_top_overlap(table)
    row = summary.loc[(summary["cell_type"] == "CD4") & (summary["top_n"] == 100)].iloc[0]
    assert row["jaccard_overlap"] == pytest.approx(1.0)


def test_filter_cell_type(detection_df: pd.DataFrame) -> None:
    table = compute_percentiles(
        compute_clone_ranks(detection_df.loc[detection_df["cell_type"] == "CD8"])
    )
    assert len(table) == 1
    assert table.iloc[0]["clonotype_key"] == "clone_d"


def test_run_rank_concordance_no_plots(
    detection_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs"
    detection_df.to_csv(input_path, index=False)

    run_rank_concordance(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=False,
    )

    out_dir = output_dir / "rank_concordance"
    assert (out_dir / "rank_table.csv").exists()
    assert (out_dir / "rank_correlation_summary.csv").exists()
    assert not (out_dir / "rank_scatter.png").exists()


def test_run_rank_concordance_creates_plots(
    detection_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs_plots"
    detection_df.to_csv(input_path, index=False)

    run_rank_concordance(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=True,
    )

    out_dir = output_dir / "rank_concordance"
    assert (out_dir / "rank_scatter.png").exists()
    assert (out_dir / "percentile_heatmap.png").exists()
    assert (out_dir / "top_overlap_curve.png").exists()

    correlation = pd.read_csv(out_dir / "rank_correlation_summary.csv")
    assert list(correlation.columns) == RANK_CORRELATION_COLUMNS


def test_plot_functions_create_png(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    table = compute_percentiles(compute_clone_ranks(detection_df))
    overlap = compute_top_overlap(table)
    plot_rank_scatter(table, tmp_path / "scatter.png")
    plot_percentile_heatmap(table, tmp_path / "heatmap.png")
    plot_top_overlap_curve(overlap, tmp_path / "curve.png")
    assert (tmp_path / "scatter.png").exists()
    assert (tmp_path / "heatmap.png").exists()
    assert (tmp_path / "curve.png").exists()
