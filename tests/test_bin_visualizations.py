"""Tests for bin-level target abundance visualizations."""

from pathlib import Path

import pandas as pd
import pytest

from tcr_bcr_tools.bin_visualizations import (
    BIN_SUMMARY_FILENAME,
    BOXPLOT_FILENAME,
    SCATTER_FILENAME,
    TARGET_ABUNDANCE_SUMMARY_COLUMNS,
    export_bin_visualizations,
    get_bin_points,
    plot_bin_boxplot,
    plot_bin_scatter,
    summarize_target_abundance_by_bin,
)
from tcr_bcr_tools.detection_curves import build_detection_points


def _points_df() -> pd.DataFrame:
    detection_df = pd.DataFrame(
        [
            {
                "patient": "p1",
                "cell_type": "CD4",
                "clonotype_key": "clone_a",
                "sf_cells": 4,
                "blood_cells": 2,
                "detected_in_sf": True,
                "detected_in_blood": True,
                "shared_clone": True,
                "sf_fraction": 0.04,
                "blood_fraction": 0.02,
            },
            {
                "patient": "p1",
                "cell_type": "CD4",
                "clonotype_key": "clone_b",
                "sf_cells": 5,
                "blood_cells": 0,
                "detected_in_sf": True,
                "detected_in_blood": False,
                "shared_clone": False,
                "sf_fraction": 0.05,
                "blood_fraction": 0.0,
            },
            {
                "patient": "p1",
                "cell_type": "CD4",
                "clonotype_key": "clone_c",
                "sf_cells": 60,
                "blood_cells": 8,
                "detected_in_sf": True,
                "detected_in_blood": True,
                "shared_clone": True,
                "sf_fraction": 0.06,
                "blood_fraction": 0.08,
            },
            {
                "patient": "p1",
                "cell_type": "CD4",
                "clonotype_key": "clone_d",
                "sf_cells": 75,
                "blood_cells": 0,
                "detected_in_sf": True,
                "detected_in_blood": False,
                "shared_clone": False,
                "sf_fraction": 0.075,
                "blood_fraction": 0.0,
            },
        ]
    )
    return build_detection_points(detection_df)


@pytest.fixture
def points_df() -> pd.DataFrame:
    return _points_df()


def test_mean_target_cells_all_includes_zeros(points_df: pd.DataFrame) -> None:
    summary = summarize_target_abundance_by_bin(points_df)
    row = summary.loc[
        (summary["direction"] == "sf_to_blood")
        & (summary["cell_type"] == "CD4")
        & (summary["bin_label"] == "3-5")
    ].iloc[0]
    assert row["mean_target_cells_all"] == pytest.approx(1.0)


def test_mean_target_cells_detected_only(points_df: pd.DataFrame) -> None:
    summary = summarize_target_abundance_by_bin(points_df)
    row = summary.loc[
        (summary["direction"] == "sf_to_blood")
        & (summary["cell_type"] == "CD4")
        & (summary["bin_label"] == "51-100")
    ].iloc[0]
    assert row["mean_target_cells_detected_only"] == pytest.approx(8.0)


def test_median_target_cells_detected_only(points_df: pd.DataFrame) -> None:
    summary = summarize_target_abundance_by_bin(points_df)
    row = summary.loc[
        (summary["direction"] == "sf_to_blood")
        & (summary["cell_type"] == "CD4")
        & (summary["bin_label"] == "51-100")
    ].iloc[0]
    assert row["median_target_cells_detected_only"] == pytest.approx(8.0)


def test_quantiles_target_cells_detected_only(points_df: pd.DataFrame) -> None:
    summary = summarize_target_abundance_by_bin(points_df)
    row = summary.loc[
        (summary["direction"] == "sf_to_blood")
        & (summary["cell_type"] == "CD4")
        & (summary["bin_label"] == "51-100")
    ].iloc[0]
    assert row["q25_target_cells_detected_only"] == pytest.approx(8.0)
    assert row["q75_target_cells_detected_only"] == pytest.approx(8.0)


def test_get_bin_points(points_df: pd.DataFrame) -> None:
    bin_points = get_bin_points(
        points_df, direction="sf_to_blood", bin_label="51-100", cell_type="CD4"
    )
    assert set(bin_points["clonotype_key"]) == {"clone_c", "clone_d"}


def test_get_bin_points_detected_only(points_df: pd.DataFrame) -> None:
    bin_points = get_bin_points(
        points_df,
        direction="sf_to_blood",
        bin_label="51-100",
        cell_type="CD4",
        detected_only=True,
    )
    assert set(bin_points["clonotype_key"]) == {"clone_c"}


def test_plot_bin_scatter_creates_png(points_df: pd.DataFrame, tmp_path: Path) -> None:
    bin_points = get_bin_points(
        points_df, direction="sf_to_blood", bin_label="3-5", cell_type="CD4"
    )
    output_path = tmp_path / "scatter.png"
    plot_bin_scatter(
        bin_points,
        direction="sf_to_blood",
        bin_label="3-5",
        output_path=output_path,
        cell_type="CD4",
    )
    assert output_path.exists()


def test_plot_bin_boxplot_creates_png(points_df: pd.DataFrame, tmp_path: Path) -> None:
    bin_points = get_bin_points(
        points_df, direction="sf_to_blood", bin_label="51-100", cell_type="CD4"
    )
    output_path = tmp_path / "boxplot.png"
    plot_bin_boxplot(
        bin_points,
        direction="sf_to_blood",
        bin_label="51-100",
        output_path=output_path,
        cell_type="CD4",
    )
    assert output_path.exists()


def test_plot_bin_boxplot_placeholder_when_no_detected(
    points_df: pd.DataFrame, tmp_path: Path
) -> None:
    bin_points = get_bin_points(
        points_df, direction="sf_to_blood", bin_label="3-5", cell_type="CD4"
    )
    output_path = tmp_path / "boxplot_empty.png"
    plot_bin_boxplot(
        bin_points,
        direction="sf_to_blood",
        bin_label="3-5",
        output_path=output_path,
        cell_type="CD4",
    )
    assert output_path.exists()


def test_export_bin_visualizations_structure(
    points_df: pd.DataFrame, tmp_path: Path
) -> None:
    bins_dir = tmp_path / "bins"
    global_summary_path = tmp_path / "target_abundance_by_bin_summary.csv"
    export_bin_visualizations(
        points_df,
        output_dir=bins_dir,
        cell_type="CD4",
        global_summary_path=global_summary_path,
    )

    assert global_summary_path.exists()
    global_summary = pd.read_csv(global_summary_path)
    assert list(global_summary.columns) == TARGET_ABUNDANCE_SUMMARY_COLUMNS

    bin_dir = bins_dir / "sf_to_blood" / "51-100"
    assert (bin_dir / SCATTER_FILENAME).exists()
    assert (bin_dir / BOXPLOT_FILENAME).exists()
    assert (bin_dir / BIN_SUMMARY_FILENAME).exists()

    bin_summary = pd.read_csv(bin_dir / BIN_SUMMARY_FILENAME)
    assert len(bin_summary) == 1
    assert bin_summary.iloc[0]["n_source_clones"] == 2
    assert bin_summary.iloc[0]["n_target_detected"] == 1
