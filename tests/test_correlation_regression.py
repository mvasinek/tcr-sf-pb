"""Tests for correlation and regression analysis."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tcr_bcr_tools.correlation_regression import (
    CORRELATION_SUMMARY_COLUMNS,
    DEFAULT_PSEUDOCOUNT,
    PREDICTION_COLUMNS,
    REGRESSION_SUMMARY_COLUMNS,
    add_log_fractions,
    compute_correlation_summary,
    compute_regression_summary,
    filter_scope,
    fit_linear_regression,
    run_correlation_regression,
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
                "clone_a",
                sf_cells=30,
                blood_cells=30,
                sf_fraction=0.30,
                blood_fraction=0.30,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "clone_b",
                sf_cells=20,
                blood_cells=20,
                sf_fraction=0.20,
                blood_fraction=0.20,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "clone_c",
                sf_cells=10,
                blood_cells=10,
                sf_fraction=0.10,
                blood_fraction=0.10,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "clone_sf_only",
                sf_cells=5,
                blood_cells=0,
                sf_fraction=0.05,
                blood_fraction=0.0,
                detected_in_sf=True,
                detected_in_blood=False,
            ),
            _detection_row(
                "clone_blood_only",
                sf_cells=0,
                blood_cells=4,
                sf_fraction=0.0,
                blood_fraction=0.04,
                detected_in_sf=False,
                detected_in_blood=True,
            ),
            _detection_row(
                "clone_cd8",
                sf_cells=12,
                blood_cells=8,
                sf_fraction=0.12,
                blood_fraction=0.08,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
            _detection_row(
                "clone_cd8_b",
                sf_cells=6,
                blood_cells=4,
                sf_fraction=0.06,
                blood_fraction=0.04,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
            _detection_row(
                "clone_cd8_c",
                sf_cells=2,
                blood_cells=2,
                sf_fraction=0.02,
                blood_fraction=0.02,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
        ]
    )


def test_log_blood_fraction(detection_df: pd.DataFrame) -> None:
    result = add_log_fractions(detection_df)
    expected = np.log10(0.30 + DEFAULT_PSEUDOCOUNT)
    assert result.loc[result["clonotype_key"] == "clone_a", "log_blood_fraction"].iloc[
        0
    ] == pytest.approx(expected)


def test_log_sf_fraction(detection_df: pd.DataFrame) -> None:
    result = add_log_fractions(detection_df)
    expected = np.log10(0.0 + DEFAULT_PSEUDOCOUNT)
    assert result.loc[
        result["clonotype_key"] == "clone_blood_only", "log_sf_fraction"
    ].iloc[0] == pytest.approx(expected)


def test_filter_scope_all_clones(detection_df: pd.DataFrame) -> None:
    assert len(filter_scope(detection_df, "all_clones")) == len(detection_df)


def test_filter_scope_shared_clones(detection_df: pd.DataFrame) -> None:
    shared = filter_scope(detection_df, "shared_clones")
    assert set(shared["clonotype_key"]) == {
        "clone_a",
        "clone_b",
        "clone_c",
        "clone_cd8",
        "clone_cd8_b",
        "clone_cd8_c",
    }


def test_filter_scope_blood_detected(detection_df: pd.DataFrame) -> None:
    blood = filter_scope(detection_df, "blood_detected")
    assert "clone_sf_only" not in set(blood["clonotype_key"])
    assert "clone_blood_only" in set(blood["clonotype_key"])


def test_filter_scope_sf_detected(detection_df: pd.DataFrame) -> None:
    sf = filter_scope(detection_df, "sf_detected")
    assert "clone_blood_only" not in set(sf["clonotype_key"])
    assert "clone_sf_only" in set(sf["clonotype_key"])


def test_pearson_correlation(detection_df: pd.DataFrame) -> None:
    df = add_log_fractions(detection_df)
    summary = compute_correlation_summary(df, scopes=["shared_clones"])
    cd4 = summary.loc[summary["cell_type"] == "CD4"].iloc[0]
    assert cd4["pearson_fraction"] == pytest.approx(1.0)


def test_spearman_correlation(detection_df: pd.DataFrame) -> None:
    df = add_log_fractions(detection_df)
    summary = compute_correlation_summary(df, scopes=["shared_clones"])
    cd4 = summary.loc[summary["cell_type"] == "CD4"].iloc[0]
    assert cd4["spearman_fraction"] == pytest.approx(1.0)


def test_kendall_correlation(detection_df: pd.DataFrame) -> None:
    df = add_log_fractions(detection_df)
    summary = compute_correlation_summary(df, scopes=["shared_clones"])
    cd4 = summary.loc[summary["cell_type"] == "CD4"].iloc[0]
    assert cd4["kendall_fraction"] == pytest.approx(1.0)


def test_linear_regression_perfect_relationship() -> None:
    df = add_log_fractions(
        pd.DataFrame(
            [
                _detection_row("a", sf_fraction=0.01, blood_fraction=0.01, sf_cells=1, blood_cells=1),
                _detection_row("b", sf_fraction=0.10, blood_fraction=0.10, sf_cells=2, blood_cells=2),
                _detection_row("c", sf_fraction=1.00, blood_fraction=1.00, sf_cells=3, blood_cells=3),
            ]
        )
    )
    fit = fit_linear_regression(df)
    predicted = fit["intercept"] + fit["slope"] * df["log_blood_fraction"]
    assert np.allclose(predicted, df["log_sf_fraction"], rtol=1e-6)


def test_r_squared_perfect_fit() -> None:
    df = add_log_fractions(
        pd.DataFrame(
            [
                _detection_row("a", sf_fraction=0.01, blood_fraction=0.01, sf_cells=1, blood_cells=1),
                _detection_row("b", sf_fraction=0.10, blood_fraction=0.10, sf_cells=2, blood_cells=2),
                _detection_row("c", sf_fraction=1.00, blood_fraction=1.00, sf_cells=3, blood_cells=3),
            ]
        )
    )
    fit = fit_linear_regression(df)
    assert fit["r_squared"] == pytest.approx(1.0)


def test_rmse_perfect_fit() -> None:
    df = add_log_fractions(
        pd.DataFrame(
            [
                _detection_row("a", sf_fraction=0.01, blood_fraction=0.01, sf_cells=1, blood_cells=1),
                _detection_row("b", sf_fraction=0.10, blood_fraction=0.10, sf_cells=2, blood_cells=2),
                _detection_row("c", sf_fraction=1.00, blood_fraction=1.00, sf_cells=3, blood_cells=3),
            ]
        )
    )
    fit = fit_linear_regression(df)
    assert fit["rmse"] == pytest.approx(0.0)


def test_mae_perfect_fit() -> None:
    df = add_log_fractions(
        pd.DataFrame(
            [
                _detection_row("a", sf_fraction=0.01, blood_fraction=0.01, sf_cells=1, blood_cells=1),
                _detection_row("b", sf_fraction=0.10, blood_fraction=0.10, sf_cells=2, blood_cells=2),
                _detection_row("c", sf_fraction=1.00, blood_fraction=1.00, sf_cells=3, blood_cells=3),
            ]
        )
    )
    fit = fit_linear_regression(df)
    assert fit["mae"] == pytest.approx(0.0)


def test_regression_predictions_columns(detection_df: pd.DataFrame) -> None:
    df = add_log_fractions(detection_df)
    _, predictions = compute_regression_summary(df, scopes=["all_clones"])
    assert list(predictions.columns) == PREDICTION_COLUMNS
    assert set(predictions["scope"]) == {"all_clones"}

    for cell_type in predictions["cell_type"].unique():
        cell_preds = predictions.loc[predictions["cell_type"] == cell_type]
        fit = fit_linear_regression(df.loc[df["cell_type"] == cell_type])
        expected_log = fit["intercept"] + fit["slope"] * cell_preds["log_blood_fraction"]
        assert np.allclose(cell_preds["predicted_log_sf_fraction"], expected_log)
        assert np.allclose(
            cell_preds["residual_log_sf_fraction"],
            cell_preds["log_sf_fraction"] - expected_log,
        )


def test_filter_cell_type(detection_df: pd.DataFrame) -> None:
    df = add_log_fractions(detection_df.loc[detection_df["cell_type"] == "CD8"])
    summary = compute_correlation_summary(df, scopes=["all_clones"])
    assert set(summary["cell_type"]) == {"CD8"}


def test_scope_parameter(detection_df: pd.DataFrame) -> None:
    df = add_log_fractions(detection_df)
    summary = compute_correlation_summary(df, scopes=["shared_clones"])
    assert set(summary["scope"]) == {"shared_clones"}
    assert list(summary.columns) == CORRELATION_SUMMARY_COLUMNS


def test_run_no_plots(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs"
    detection_df.to_csv(input_path, index=False)

    run_correlation_regression(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=False,
    )

    out_dir = output_dir / "correlation_regression"
    assert (out_dir / "correlation_summary.csv").exists()
    assert (out_dir / "regression_summary.csv").exists()
    assert (out_dir / "regression_predictions.csv").exists()
    assert not (out_dir / "blood_vs_sf_fraction_scatter.png").exists()


def test_run_creates_all_plots(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs_plots"
    detection_df.to_csv(input_path, index=False)

    run_correlation_regression(
        input_path=input_path,
        output_dir=output_dir,
        make_plots=True,
    )

    out_dir = output_dir / "correlation_regression"
    assert (out_dir / "blood_vs_sf_fraction_scatter.png").exists()
    assert (out_dir / "blood_vs_sf_log_fraction_scatter.png").exists()
    assert (out_dir / "regression_fit_by_cell_type.png").exists()
    assert (out_dir / "residuals_by_cell_type.png").exists()


def test_regression_summary_columns(detection_df: pd.DataFrame) -> None:
    df = add_log_fractions(detection_df)
    summary, _ = compute_regression_summary(df)
    assert list(summary.columns) == REGRESSION_SUMMARY_COLUMNS
    assert len(summary["scope"].unique()) == 4
