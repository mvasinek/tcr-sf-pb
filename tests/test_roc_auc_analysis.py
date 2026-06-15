"""Tests for ROC/AUC analysis."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tcr_bcr_tools.roc_auc_analysis import (
    DEFAULT_PREDICTORS,
    PREDICTION_SCORES_COLUMNS,
    ROC_AUC_SUMMARY_COLUMNS,
    compute_binary_metrics,
    ensure_blood_ranks,
    prepare_prediction_scores,
    run_roc_auc_analysis,
    run_roc_auc_cli,
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
                "expanded_high_blood",
                sf_cells=20,
                blood_cells=20,
                sf_fraction=0.02,
                blood_fraction=0.02,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "expanded_low_blood",
                sf_cells=15,
                blood_cells=1,
                sf_fraction=0.015,
                blood_fraction=0.001,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "not_expanded_high_blood",
                sf_cells=1,
                blood_cells=10,
                sf_fraction=0.001,
                blood_fraction=0.01,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "not_expanded_low_blood",
                sf_cells=1,
                blood_cells=1,
                sf_fraction=0.0001,
                blood_fraction=0.0001,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
            ),
            _detection_row(
                "cd8_expanded",
                sf_cells=12,
                blood_cells=8,
                sf_fraction=0.02,
                blood_fraction=0.008,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
            _detection_row(
                "cd8_not_expanded",
                sf_cells=1,
                blood_cells=2,
                sf_fraction=0.001,
                blood_fraction=0.002,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
            _detection_row(
                "cd8_extra",
                sf_cells=1,
                blood_cells=1,
                sf_fraction=0.0001,
                blood_fraction=0.0001,
                detected_in_sf=True,
                detected_in_blood=True,
                shared_clone=True,
                cell_type="CD8",
            ),
        ]
    )


def test_sf_expanded_fraction_threshold(detection_df: pd.DataFrame) -> None:
    scores = prepare_prediction_scores(
        detection_df, expansion_method="fraction", expansion_threshold=0.005
    )
    expanded = scores.loc[scores["clonotype_key"] == "expanded_high_blood"].iloc[0]
    not_expanded = scores.loc[
        scores["clonotype_key"] == "not_expanded_low_blood"
    ].iloc[0]
    assert expanded["sf_expanded"] == True  # noqa: E712
    assert not_expanded["sf_expanded"] == False  # noqa: E712


def test_sf_expanded_cells_threshold(detection_df: pd.DataFrame) -> None:
    scores = prepare_prediction_scores(
        detection_df, expansion_method="cells", expansion_threshold=5
    )
    expanded = scores.loc[scores["clonotype_key"] == "expanded_high_blood"].iloc[0]
    not_expanded = scores.loc[
        scores["clonotype_key"] == "not_expanded_low_blood"
    ].iloc[0]
    assert expanded["sf_expanded"] == True  # noqa: E712
    assert not_expanded["sf_expanded"] == False  # noqa: E712


def test_log_blood_fraction(detection_df: pd.DataFrame) -> None:
    scores = prepare_prediction_scores(detection_df)
    value = scores.loc[scores["clonotype_key"] == "expanded_high_blood", "log_blood_fraction"].iloc[
        0
    ]
    assert value == pytest.approx(np.log10(0.02 + 1e-6))


def test_blood_rank(detection_df: pd.DataFrame) -> None:
    ranked = ensure_blood_ranks(detection_df)
    assert ranked["blood_rank"].notna().all()
    assert ranked.loc[ranked["clonotype_key"] == "expanded_high_blood", "blood_rank"].iloc[0] == 1


def test_blood_percentile(detection_df: pd.DataFrame) -> None:
    ranked = ensure_blood_ranks(detection_df)
    top = ranked.loc[ranked["clonotype_key"] == "expanded_high_blood", "blood_percentile"].iloc[0]
    assert top == pytest.approx(1.0)


def test_blood_rank_inverse(detection_df: pd.DataFrame) -> None:
    scores = prepare_prediction_scores(detection_df)
    inverse = scores.loc[scores["clonotype_key"] == "expanded_high_blood", "blood_rank_inverse"].iloc[
        0
    ]
    assert inverse == pytest.approx(1.0)


def test_roc_auc_perfect_predictor() -> None:
    y_true = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.9, 0.8, 0.2, 0.1])
    metrics = compute_binary_metrics(y_true, scores)
    assert metrics["auc"] == pytest.approx(1.0)


def test_roc_auc_opposite_predictor() -> None:
    y_true = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.1, 0.2, 0.8, 0.9])
    metrics = compute_binary_metrics(y_true, scores)
    assert metrics["auc"] == pytest.approx(0.0)


def test_average_precision() -> None:
    y_true = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.9, 0.8, 0.2, 0.1])
    metrics = compute_binary_metrics(y_true, scores)
    assert metrics["average_precision"] == pytest.approx(1.0)


def test_best_youden_threshold() -> None:
    y_true = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.9, 0.7, 0.3, 0.1])
    metrics = compute_binary_metrics(y_true, scores)
    assert metrics["best_youden_j"] == pytest.approx(1.0)
    assert metrics["best_threshold"] == pytest.approx(0.7)


def test_sensitivity_at_best_threshold() -> None:
    y_true = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.9, 0.7, 0.3, 0.1])
    metrics = compute_binary_metrics(y_true, scores)
    assert metrics["sensitivity_at_best_threshold"] == pytest.approx(1.0)


def test_specificity_at_best_threshold() -> None:
    y_true = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.9, 0.7, 0.3, 0.1])
    metrics = compute_binary_metrics(y_true, scores)
    assert metrics["specificity_at_best_threshold"] == pytest.approx(1.0)


def test_no_positive_cases() -> None:
    y_true = pd.Series([0, 0, 0])
    scores = pd.Series([0.1, 0.2, 0.3])
    metrics = compute_binary_metrics(y_true, scores)
    assert np.isnan(metrics["auc"])
    assert metrics["n_positive"] == 0


def test_no_negative_cases() -> None:
    y_true = pd.Series([1, 1, 1])
    scores = pd.Series([0.1, 0.2, 0.3])
    metrics = compute_binary_metrics(y_true, scores)
    assert np.isnan(metrics["auc"])
    assert metrics["n_negative"] == 0


def test_zero_variance_predictor() -> None:
    y_true = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.5, 0.5, 0.5, 0.5])
    metrics = compute_binary_metrics(y_true, scores)
    assert np.isnan(metrics["auc"])


def test_filter_cell_type(detection_df: pd.DataFrame) -> None:
    summary, _, _, scores = run_roc_auc_analysis(
        detection_df,
        predictors=["blood_fraction"],
        cell_type="CD8",
    )
    assert set(summary["cell_type"]) == {"CD8"}
    assert set(scores["cell_type"]) == {"CD8"}


def test_predictors_parameter(detection_df: pd.DataFrame) -> None:
    summary, _, _, _ = run_roc_auc_analysis(
        detection_df,
        predictors=["blood_fraction", "blood_cells"],
    )
    assert set(summary["predictor"]) == {"blood_fraction", "blood_cells"}


def test_run_no_plots(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs"
    detection_df.to_csv(input_path, index=False)

    run_roc_auc_cli(
        input_path=input_path,
        output_dir=output_dir,
        predictors=["blood_fraction"],
        make_plots=False,
    )

    out_dir = output_dir / "roc_auc"
    assert (out_dir / "roc_auc_summary.csv").exists()
    assert (out_dir / "roc_curve_points.csv").exists()
    assert (out_dir / "pr_curve_points.csv").exists()
    assert (out_dir / "prediction_scores.csv").exists()
    assert not (out_dir / "roc_curves_by_cell_type.png").exists()


def test_run_creates_all_plots(detection_df: pd.DataFrame, tmp_path: Path) -> None:
    input_path = tmp_path / "paired_detection_table.csv"
    output_dir = tmp_path / "outputs_plots"
    detection_df.to_csv(input_path, index=False)

    run_roc_auc_cli(
        input_path=input_path,
        output_dir=output_dir,
        predictors=DEFAULT_PREDICTORS,
        make_plots=True,
    )

    out_dir = output_dir / "roc_auc"
    assert (out_dir / "roc_curves_by_cell_type.png").exists()
    assert (out_dir / "pr_curves_by_cell_type.png").exists()
    assert (out_dir / "auc_by_predictor.png").exists()
    assert (out_dir / "score_distribution_by_class.png").exists()


def test_prediction_scores_columns(detection_df: pd.DataFrame) -> None:
    scores = prepare_prediction_scores(detection_df)
    assert list(scores.columns) == PREDICTION_SCORES_COLUMNS


def test_summary_columns(detection_df: pd.DataFrame) -> None:
    summary, _, _, _ = run_roc_auc_analysis(
        detection_df,
        predictors=["blood_fraction"],
    )
    assert list(summary.columns) == ROC_AUC_SUMMARY_COLUMNS
