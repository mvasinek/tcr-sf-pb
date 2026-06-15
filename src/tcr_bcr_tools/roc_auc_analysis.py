"""ROC/AUC analysis for predicting SF expansion from blood-derived features."""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from tcr_bcr_tools.expansion_concordance import classify_expansion
from tcr_bcr_tools.rank_concordance import compute_clone_ranks, compute_percentiles

DEFAULT_PSEUDOCOUNT = 1e-6
DEFAULT_EXPANSION_METHOD = "fraction"
DEFAULT_EXPANSION_THRESHOLD = 0.005
OUTPUT_DIRNAME = "roc_auc"

DEFAULT_PREDICTORS = [
    "blood_fraction",
    "blood_cells",
    "blood_percentile",
    "blood_rank_inverse",
    "log_blood_fraction",
]

ROC_AUC_SUMMARY_COLUMNS = [
    "cell_type",
    "predictor",
    "expansion_method",
    "expansion_threshold",
    "n_clones",
    "n_positive",
    "n_negative",
    "auc",
    "average_precision",
    "best_threshold",
    "best_youden_j",
    "sensitivity_at_best_threshold",
    "specificity_at_best_threshold",
    "precision_at_best_threshold",
]

ROC_CURVE_COLUMNS = [
    "cell_type",
    "predictor",
    "expansion_method",
    "expansion_threshold",
    "fpr",
    "tpr",
    "threshold",
]

PR_CURVE_COLUMNS = [
    "cell_type",
    "predictor",
    "expansion_method",
    "expansion_threshold",
    "precision",
    "recall",
    "threshold",
]

PREDICTION_SCORES_COLUMNS = [
    "patient",
    "cell_type",
    "clonotype_key",
    "sf_expanded",
    "blood_cells",
    "sf_cells",
    "blood_fraction",
    "sf_fraction",
    "blood_percentile",
    "blood_rank",
    "blood_rank_inverse",
    "log_blood_fraction",
]


def ensure_blood_ranks(
    df: pd.DataFrame,
    rank_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Ensure blood rank and percentile columns are present."""
    if "blood_rank" in df.columns and "blood_percentile" in df.columns:
        return df.copy()

    if rank_df is not None:
        rank_cols = ["patient", "cell_type", "clonotype_key", "blood_rank", "blood_percentile"]
        available = [col for col in rank_cols if col in rank_df.columns]
        if len(available) == len(rank_cols):
            return df.merge(
                rank_df[rank_cols],
                on=["patient", "cell_type", "clonotype_key"],
                how="left",
            )

    rank_table = compute_percentiles(compute_clone_ranks(df))
    return df.merge(
        rank_table[["patient", "cell_type", "clonotype_key", "blood_rank", "blood_percentile"]],
        on=["patient", "cell_type", "clonotype_key"],
        how="left",
    )


def prepare_prediction_scores(
    df: pd.DataFrame,
    expansion_method: str = DEFAULT_EXPANSION_METHOD,
    expansion_threshold: float = DEFAULT_EXPANSION_THRESHOLD,
    pseudocount: float = DEFAULT_PSEUDOCOUNT,
    rank_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build per-clone prediction scores and SF expansion labels."""
    expanded = classify_expansion(
        df,
        method=expansion_method,
        threshold=expansion_threshold,
    )
    result = ensure_blood_ranks(df, rank_df=rank_df)
    result["sf_expanded"] = expanded["sf_expanded"].values
    result["blood_rank"] = result["blood_rank"].astype(int)
    result["blood_rank_inverse"] = 1.0 / result["blood_rank"].astype(float)
    result["log_blood_fraction"] = np.log10(result["blood_fraction"] + pseudocount)
    return result[PREDICTION_SCORES_COLUMNS].copy()


def _aligned_labels(y_true: pd.Series, scores: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    valid = y_true.notna() & scores.notna()
    y_values = y_true.loc[valid].astype(int).to_numpy()
    score_values = scores.loc[valid].astype(float).to_numpy()
    return y_values, score_values


def compute_binary_metrics(
    y_true: pd.Series,
    scores: pd.Series,
) -> dict[str, float | int]:
    """Compute ROC/AUC summary metrics for one predictor."""
    y_values, score_values = _aligned_labels(y_true, scores)
    n_clones = len(y_values)
    n_positive = int(y_values.sum())
    n_negative = int(n_clones - n_positive)

    nan_metrics: dict[str, float | int] = {
        "n_clones": n_clones,
        "n_positive": n_positive,
        "n_negative": n_negative,
        "auc": np.nan,
        "average_precision": np.nan,
        "best_threshold": np.nan,
        "best_youden_j": np.nan,
        "sensitivity_at_best_threshold": np.nan,
        "specificity_at_best_threshold": np.nan,
        "precision_at_best_threshold": np.nan,
    }

    if n_positive == 0 or n_negative == 0:
        return nan_metrics
    if len(np.unique(score_values)) < 2:
        return nan_metrics

    auc = float(roc_auc_score(y_values, score_values))
    avg_precision = float(average_precision_score(y_values, score_values))
    fpr, tpr, thresholds = roc_curve(y_values, score_values)
    youden_j = tpr - fpr
    best_idx = int(np.argmax(youden_j))
    best_threshold = float(thresholds[best_idx])
    sensitivity = float(tpr[best_idx])
    specificity = float(1.0 - fpr[best_idx])

    predicted_positive = score_values >= best_threshold
    true_positive = int(np.sum(predicted_positive & (y_values == 1)))
    predicted_positive_count = int(np.sum(predicted_positive))
    precision = (
        true_positive / predicted_positive_count if predicted_positive_count > 0 else np.nan
    )

    return {
        "n_clones": n_clones,
        "n_positive": n_positive,
        "n_negative": n_negative,
        "auc": auc,
        "average_precision": avg_precision,
        "best_threshold": best_threshold,
        "best_youden_j": float(youden_j[best_idx]),
        "sensitivity_at_best_threshold": sensitivity,
        "specificity_at_best_threshold": specificity,
        "precision_at_best_threshold": float(precision),
    }


def compute_roc_curve_points(
    y_true: pd.Series,
    scores: pd.Series,
    *,
    cell_type: str,
    predictor: str,
    expansion_method: str,
    expansion_threshold: float,
) -> pd.DataFrame:
    """Compute ROC curve points for one predictor."""
    y_values, score_values = _aligned_labels(y_true, scores)
    n_positive = int(y_values.sum())
    n_negative = int(len(y_values) - n_positive)

    if n_positive == 0 or n_negative == 0 or len(np.unique(score_values)) < 2:
        return pd.DataFrame(columns=ROC_CURVE_COLUMNS)

    fpr, tpr, thresholds = roc_curve(y_values, score_values)
    return pd.DataFrame(
        {
            "cell_type": cell_type,
            "predictor": predictor,
            "expansion_method": expansion_method,
            "expansion_threshold": expansion_threshold,
            "fpr": fpr,
            "tpr": tpr,
            "threshold": thresholds,
        }
    )


def compute_pr_curve_points(
    y_true: pd.Series,
    scores: pd.Series,
    *,
    cell_type: str,
    predictor: str,
    expansion_method: str,
    expansion_threshold: float,
) -> pd.DataFrame:
    """Compute precision-recall curve points for one predictor."""
    y_values, score_values = _aligned_labels(y_true, scores)
    n_positive = int(y_values.sum())
    n_negative = int(len(y_values) - n_positive)

    if n_positive == 0 or n_negative == 0 or len(np.unique(score_values)) < 2:
        return pd.DataFrame(columns=PR_CURVE_COLUMNS)

    precision, recall, thresholds = precision_recall_curve(y_values, score_values)
    threshold_values = np.append(thresholds, np.nan)
    return pd.DataFrame(
        {
            "cell_type": cell_type,
            "predictor": predictor,
            "expansion_method": expansion_method,
            "expansion_threshold": expansion_threshold,
            "precision": precision,
            "recall": recall,
            "threshold": threshold_values,
        }
    )


def run_roc_auc_analysis(
    df: pd.DataFrame,
    predictors: list[str],
    expansion_method: str = DEFAULT_EXPANSION_METHOD,
    expansion_threshold: float = DEFAULT_EXPANSION_THRESHOLD,
    cell_type: str | None = None,
    pseudocount: float = DEFAULT_PSEUDOCOUNT,
    rank_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run ROC/AUC analysis for each cell type and predictor."""
    working_df = df.copy()
    if cell_type is not None:
        working_df = working_df.loc[working_df["cell_type"] == cell_type].copy()

    scores_df = prepare_prediction_scores(
        working_df,
        expansion_method=expansion_method,
        expansion_threshold=expansion_threshold,
        pseudocount=pseudocount,
        rank_df=rank_df,
    )

    summary_records: list[dict] = []
    roc_frames: list[pd.DataFrame] = []
    pr_frames: list[pd.DataFrame] = []

    for current_cell_type, group in scores_df.groupby("cell_type", dropna=False):
        cell_type_str = str(current_cell_type)
        for predictor in predictors:
            if predictor not in group.columns:
                raise ValueError(f"Unknown predictor '{predictor}'.")

            metrics = compute_binary_metrics(group["sf_expanded"], group[predictor])
            if metrics["n_positive"] == 0 or metrics["n_negative"] == 0:
                warnings.warn(
                    f"Skipping ROC/PR curves for {cell_type_str} + {predictor}: "
                    f"n_positive={metrics['n_positive']}, n_negative={metrics['n_negative']}.",
                    stacklevel=2,
                )
            elif len(group[predictor].dropna().unique()) < 2:
                warnings.warn(
                    f"Skipping ROC/PR curves for {cell_type_str} + {predictor}: "
                    "predictor has zero variance.",
                    stacklevel=2,
                )

            summary_records.append(
                {
                    "cell_type": cell_type_str,
                    "predictor": predictor,
                    "expansion_method": expansion_method,
                    "expansion_threshold": expansion_threshold,
                    **metrics,
                }
            )

            roc_points = compute_roc_curve_points(
                group["sf_expanded"],
                group[predictor],
                cell_type=cell_type_str,
                predictor=predictor,
                expansion_method=expansion_method,
                expansion_threshold=expansion_threshold,
            )
            if not roc_points.empty:
                roc_frames.append(roc_points)

            pr_points = compute_pr_curve_points(
                group["sf_expanded"],
                group[predictor],
                cell_type=cell_type_str,
                predictor=predictor,
                expansion_method=expansion_method,
                expansion_threshold=expansion_threshold,
            )
            if not pr_points.empty:
                pr_frames.append(pr_points)

    summary = (
        pd.DataFrame(columns=ROC_AUC_SUMMARY_COLUMNS)
        if not summary_records
        else pd.DataFrame(summary_records)[ROC_AUC_SUMMARY_COLUMNS]
    )
    roc_points_df = (
        pd.DataFrame(columns=ROC_CURVE_COLUMNS)
        if not roc_frames
        else pd.concat(roc_frames, ignore_index=True)[ROC_CURVE_COLUMNS]
    )
    pr_points_df = (
        pd.DataFrame(columns=PR_CURVE_COLUMNS)
        if not pr_frames
        else pd.concat(pr_frames, ignore_index=True)[PR_CURVE_COLUMNS]
    )
    return summary, roc_points_df, pr_points_df, scores_df


def plot_roc_curves(
    roc_points_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot ROC curves by cell type and predictor."""
    cell_types = sorted(summary_df["cell_type"].dropna().unique())
    n_panels = max(len(cell_types), 1)
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 4), squeeze=False)

    for index, cell_type in enumerate(cell_types):
        ax = axes[0, index]
        cell_points = roc_points_df.loc[roc_points_df["cell_type"] == cell_type]
        predictors = sorted(cell_points["predictor"].dropna().unique())

        for predictor in predictors:
            predictor_points = cell_points.loc[cell_points["predictor"] == predictor]
            ax.plot(
                predictor_points["fpr"],
                predictor_points["tpr"],
                label=predictor,
            )

        ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
        ax.set_title(str(cell_type))
        ax.set_xlabel("fpr")
        ax.set_ylabel("tpr")
        ax.legend(fontsize=7)

    if not cell_types:
        axes[0, 0].set_title("ROC curves by cell type")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.suptitle("ROC curves by cell type")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_pr_curves(
    pr_points_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot precision-recall curves by cell type and predictor."""
    cell_types = sorted(summary_df["cell_type"].dropna().unique())
    n_panels = max(len(cell_types), 1)
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 4), squeeze=False)

    for index, cell_type in enumerate(cell_types):
        ax = axes[0, index]
        cell_points = pr_points_df.loc[pr_points_df["cell_type"] == cell_type]
        predictors = sorted(cell_points["predictor"].dropna().unique())

        for predictor in predictors:
            predictor_points = cell_points.loc[cell_points["predictor"] == predictor]
            ax.plot(
                predictor_points["recall"],
                predictor_points["precision"],
                label=predictor,
            )

        ax.set_title(str(cell_type))
        ax.set_xlabel("recall")
        ax.set_ylabel("precision")
        ax.legend(fontsize=7)

    if not cell_types:
        axes[0, 0].set_title("PR curves by cell type")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.suptitle("Precision-recall curves by cell type")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_auc_by_predictor(
    summary_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot AUC by predictor and cell type."""
    plot_df = summary_df.dropna(subset=["auc"]).copy()
    fig, ax = plt.subplots(figsize=(9, 5))

    if plot_df.empty:
        ax.set_title("AUC by predictor")
    else:
        cell_types = sorted(plot_df["cell_type"].unique())
        predictors = sorted(plot_df["predictor"].unique())
        x_positions = np.arange(len(predictors))
        bar_width = 0.8 / max(len(cell_types), 1)

        for index, cell_type in enumerate(cell_types):
            cell_df = plot_df.loc[plot_df["cell_type"] == cell_type]
            values = [
                cell_df.loc[cell_df["predictor"] == predictor, "auc"].iloc[0]
                if not cell_df.loc[cell_df["predictor"] == predictor].empty
                else np.nan
                for predictor in predictors
            ]
            offsets = x_positions + (index - (len(cell_types) - 1) / 2) * bar_width
            ax.bar(offsets, values, width=bar_width, label=str(cell_type))

        ax.set_xticks(x_positions, predictors, rotation=20, ha="right")
        ax.set_ylim(0, 1)
        ax.set_xlabel("predictor")
        ax.set_ylabel("auc")
        ax.set_title("AUC by predictor")
        ax.legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_score_distribution_by_class(
    scores_df: pd.DataFrame,
    predictor: str,
    output_path: Path,
) -> None:
    """Plot predictor score distributions by SF expansion status."""
    fig, ax = plt.subplots(figsize=(8, 5))

    if scores_df.empty or predictor not in scores_df.columns:
        ax.set_title(f"Score distribution by class ({predictor})")
    else:
        negative = scores_df.loc[scores_df["sf_expanded"] == False, predictor]  # noqa: E712
        positive = scores_df.loc[scores_df["sf_expanded"] == True, predictor]  # noqa: E712
        ax.boxplot(
            [negative.dropna(), positive.dropna()],
            tick_labels=["sf_expanded=False", "sf_expanded=True"],
        )
        ax.set_ylabel(predictor)
        ax.set_title(f"Score distribution by class ({predictor})")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _load_optional_rank_table(output_dir: Path) -> pd.DataFrame | None:
    rank_path = output_dir / "rank_concordance" / "rank_table.csv"
    if rank_path.exists():
        return pd.read_csv(rank_path)
    return None


def run_roc_auc_cli(
    input_path: Path,
    output_dir: Path,
    predictors: list[str] | None = None,
    expansion_method: str = DEFAULT_EXPANSION_METHOD,
    expansion_threshold: float = DEFAULT_EXPANSION_THRESHOLD,
    cell_type: str | None = None,
    pseudocount: float = DEFAULT_PSEUDOCOUNT,
    make_plots: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load data, run ROC/AUC analysis, and write outputs."""
    selected_predictors = DEFAULT_PREDICTORS if predictors is None else predictors
    df = pd.read_csv(input_path)
    rank_df = _load_optional_rank_table(output_dir)

    summary, roc_points, pr_points, scores_df = run_roc_auc_analysis(
        df,
        predictors=selected_predictors,
        expansion_method=expansion_method,
        expansion_threshold=expansion_threshold,
        cell_type=cell_type,
        pseudocount=pseudocount,
        rank_df=rank_df,
    )

    out_dir = output_dir / OUTPUT_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_dir / "roc_auc_summary.csv", index=False)
    roc_points.to_csv(out_dir / "roc_curve_points.csv", index=False)
    pr_points.to_csv(out_dir / "pr_curve_points.csv", index=False)
    scores_df.to_csv(out_dir / "prediction_scores.csv", index=False)

    if make_plots:
        plot_roc_curves(roc_points, summary, out_dir / "roc_curves_by_cell_type.png")
        plot_pr_curves(pr_points, summary, out_dir / "pr_curves_by_cell_type.png")
        plot_auc_by_predictor(summary, out_dir / "auc_by_predictor.png")
        plot_score_distribution_by_class(
            scores_df,
            "log_blood_fraction",
            out_dir / "score_distribution_by_class.png",
        )

    return summary, roc_points, pr_points, scores_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze ROC/AUC for predicting SF expansion from blood features."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to paired_detection_table.csv.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Base output directory.",
    )
    parser.add_argument(
        "--expansion-method",
        choices=["fraction", "cells", "quantile"],
        default=DEFAULT_EXPANSION_METHOD,
        help="Method for defining SF expansion.",
    )
    parser.add_argument(
        "--expansion-threshold",
        type=float,
        default=DEFAULT_EXPANSION_THRESHOLD,
        help="Threshold for fraction/cells expansion or quantile cutoff.",
    )
    parser.add_argument(
        "--cell-type",
        default=None,
        help="Keep only the specified cell type.",
    )
    parser.add_argument(
        "--predictors",
        default=",".join(DEFAULT_PREDICTORS),
        help="Comma-separated list of blood-based predictors.",
    )
    parser.add_argument(
        "--pseudocount",
        type=float,
        default=DEFAULT_PSEUDOCOUNT,
        help="Pseudocount added before log10 blood fraction.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Write CSV outputs only, without PNG plots.",
    )
    args = parser.parse_args()
    predictors = [item.strip() for item in args.predictors.split(",") if item.strip()]
    run_roc_auc_cli(
        input_path=args.input,
        output_dir=args.output_dir,
        predictors=predictors,
        expansion_method=args.expansion_method,
        expansion_threshold=args.expansion_threshold,
        cell_type=args.cell_type,
        pseudocount=args.pseudocount,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
