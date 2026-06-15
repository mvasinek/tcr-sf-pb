"""Tests for detection curve analysis."""

from pathlib import Path

import pandas as pd
import pytest

from tcr_bcr_tools.detection_curves import (
    DIRECTION_OUTPUT_FILES,
    POINTS_COLUMNS,
    SUMMARY_COLUMNS,
    assign_clone_size_bin,
    build_detection_points,
    plot_detection_curve,
    run_detection_curve_analysis,
    summarize_detection_curve,
)

CLONE_SHARED = "clone_shared"
CLONE_SF_ONLY = "clone_sf_only"
CLONE_BLOOD_ONLY = "clone_blood_only"


def _detection_row(
    clonotype_key: str,
    *,
    sf_cells: int = 0,
    blood_cells: int = 0,
    detected_in_sf: bool = False,
    detected_in_blood: bool = False,
    shared_clone: bool = False,
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
        "detected_in_sf": detected_in_sf,
        "detected_in_blood": detected_in_blood,
        "shared_clone": shared_clone,
        "sf_fraction": sf_fraction,
        "blood_fraction": blood_fraction,
    }


@pytest.fixture
def detection_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _detection_row(
                CLONE_SHARED,
                sf_cells=10,
                blood_cells=2,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                sf_fraction=0.1,
                blood_fraction=0.05,
            ),
            _detection_row(
                CLONE_SF_ONLY,
                sf_cells=5,
                blood_cells=0,
                detected_in_sf=True,
                detected_in_blood=False,
                shared_clone=False,
                sf_fraction=0.05,
                blood_fraction=0.0,
            ),
            _detection_row(
                CLONE_BLOOD_ONLY,
                sf_cells=0,
                blood_cells=8,
                detected_in_sf=False,
                detected_in_blood=True,
                shared_clone=False,
                sf_fraction=0.0,
                blood_fraction=0.08,
            ),
            _detection_row(
                "clone_cd8",
                sf_cells=4,
                blood_cells=1,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                sf_fraction=0.04,
                blood_fraction=0.01,
                cell_type="CD8",
            ),
        ]
    )


def test_build_detection_points_sf_to_blood(detection_df: pd.DataFrame) -> None:
    points = build_detection_points(detection_df)
    sf_to_blood = points.loc[points["direction"] == "sf_to_blood"]

    assert set(sf_to_blood["clonotype_key"]) == {CLONE_SHARED, CLONE_SF_ONLY, "clone_cd8"}
    row = sf_to_blood.loc[sf_to_blood["clonotype_key"] == CLONE_SHARED].iloc[0]
    assert row["source_cells"] == 10
    assert row["target_cells"] == 2
    assert row["source_fraction"] == pytest.approx(0.1)
    assert row["target_fraction"] == pytest.approx(0.05)
    assert row["target_detected"] == True  # noqa: E712


def test_build_detection_points_blood_to_sf(detection_df: pd.DataFrame) -> None:
    points = build_detection_points(detection_df)
    blood_to_sf = points.loc[points["direction"] == "blood_to_sf"]

    assert set(blood_to_sf["clonotype_key"]) == {CLONE_SHARED, CLONE_BLOOD_ONLY, "clone_cd8"}
    row = blood_to_sf.loc[blood_to_sf["clonotype_key"] == CLONE_BLOOD_ONLY].iloc[0]
    assert row["source_cells"] == 8
    assert row["target_cells"] == 0
    assert row["target_detected"] == False  # noqa: E712


def test_shared_clone_in_both_directions(detection_df: pd.DataFrame) -> None:
    points = build_detection_points(detection_df)
    directions = set(
        points.loc[points["clonotype_key"] == CLONE_SHARED, "direction"]
    )
    assert directions == {"sf_to_blood", "blood_to_sf"}


@pytest.mark.parametrize(
    ("source_cells", "expected"),
    [
        (1, ("1", 1, 1)),
        (2, ("2", 2, 2)),
        (4, ("3-5", 3, 5)),
        (150, ("101+", 101, None)),
    ],
)
def test_assign_clone_size_bin(
    source_cells: int, expected: tuple[str, int, int | None]
) -> None:
    assert assign_clone_size_bin(source_cells) == expected


def test_summarize_detection_curve_counts(detection_df: pd.DataFrame) -> None:
    points = build_detection_points(detection_df.loc[detection_df["cell_type"] == "CD4"])
    summary = summarize_detection_curve(points)

    assert list(summary.columns) == SUMMARY_COLUMNS
    bin_3_5 = summary.loc[
        (summary["direction"] == "sf_to_blood")
        & (summary["cell_type"] == "CD4")
        & (summary["bin_label"] == "3-5")
    ].iloc[0]
    assert bin_3_5["n_clones"] == 1
    assert bin_3_5["n_detected"] == 0
    assert bin_3_5["detection_probability"] == pytest.approx(0.0)

    bin_6_10 = summary.loc[
        (summary["direction"] == "sf_to_blood")
        & (summary["cell_type"] == "CD4")
        & (summary["bin_label"] == "6-10")
    ].iloc[0]
    assert bin_6_10["n_clones"] == 1
    assert bin_6_10["n_detected"] == 1
    assert bin_6_10["detection_probability"] == pytest.approx(1.0)


def test_filter_cell_type(detection_df: pd.DataFrame) -> None:
    points = build_detection_points(detection_df.loc[detection_df["cell_type"] == "CD4"])
    assert (points["cell_type"] == "CD4").all()
    assert "clone_cd8" not in set(points["clonotype_key"])


def test_filter_min_source_cells(detection_df: pd.DataFrame) -> None:
    points = build_detection_points(detection_df, min_source_cells=6)
    assert CLONE_SF_ONLY not in set(points["clonotype_key"])
    assert CLONE_SHARED in set(points["clonotype_key"])


def test_run_detection_curve_analysis_writes_outputs(
    detection_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs"
    detection_df.to_csv(input_path, index=False)

    run_detection_curve_analysis(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=True,
    )

    assert (output_dir / "detection_curve_points.csv").exists()
    assert (output_dir / "detection_curve_summary.csv").exists()
    assert (output_dir / DIRECTION_OUTPUT_FILES["sf_to_blood"]).exists()
    assert (output_dir / DIRECTION_OUTPUT_FILES["blood_to_sf"]).exists()

    points = pd.read_csv(output_dir / "detection_curve_points.csv")
    assert list(points.columns) == POINTS_COLUMNS


def test_run_detection_curve_analysis_no_plots(
    detection_df: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs_no_plots"
    detection_df.to_csv(input_path, index=False)

    run_detection_curve_analysis(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=False,
    )

    assert (output_dir / "detection_curve_points.csv").exists()
    assert (output_dir / "detection_curve_summary.csv").exists()
    assert not (output_dir / DIRECTION_OUTPUT_FILES["sf_to_blood"]).exists()
    assert not (output_dir / DIRECTION_OUTPUT_FILES["blood_to_sf"]).exists()


def test_plot_detection_curve_creates_png(tmp_path: Path) -> None:
    summary = pd.DataFrame(
        [
            {
                "direction": "sf_to_blood",
                "cell_type": "CD4",
                "bin_label": "1",
                "bin_min": 1,
                "bin_max": 1,
                "n_clones": 2,
                "n_detected": 1,
                "detection_probability": 0.5,
                "mean_source_cells": 1.0,
                "median_source_cells": 1.0,
                "mean_source_fraction": 0.01,
                "median_source_fraction": 0.01,
            }
        ]
    )
    output_path = tmp_path / "plot.png"
    plot_detection_curve(summary, direction="sf_to_blood", output_path=output_path)
    assert output_path.exists()
