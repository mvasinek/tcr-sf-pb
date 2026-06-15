"""Weighted Spearman rank correlation for clone-size concordance."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tcr_bcr_tools.rank_concordance import (
    compute_clone_ranks,
    compute_percentiles,
)

WEIGHT_METHODS = {"mean_fraction", "max_fraction", "source_blood_fraction"}
DEFAULT_WEIGHT_METHOD = "max_fraction"

WEIGHTED_SUMMARY_COLUMNS = [
    "patient",
    "cell_type",
    "weight_method",
    "n_clones",
    "weight_sum",
    "weighted_spearman_fraction",
    "weighted_spearman_rank",
]

OUTPUT_DIRNAME = "weighted_rank_concordance"


def compute_clone_weights(
    df: pd.DataFrame,
    method: str = DEFAULT_WEIGHT_METHOD,
) -> pd.Series:
    """Compute per-clone weights for weighted correlation."""
    if method not in WEIGHT_METHODS:
        raise ValueError(
            f"Unsupported weight method '{method}'. "
            "Use one of: mean_fraction, max_fraction, source_blood_fraction."
        )

    if method == "mean_fraction":
        return (df["blood_fraction"] + df["sf_fraction"]) / 2
    if method == "max_fraction":
        return df[["blood_fraction", "sf_fraction"]].max(axis=1)
    return df["blood_fraction"]


def weighted_pearson_correlation(
    x: pd.Series,
    y: pd.Series,
    weights: pd.Series,
) -> float:
    """Compute weighted Pearson correlation between two series."""
    if len(x) < 3:
        return np.nan

    weight_sum = float(weights.sum())
    if weight_sum == 0:
        return np.nan

    w = weights / weight_sum
    x_values = x.astype(float)
    y_values = y.astype(float)
    mean_x = float((w * x_values).sum())
    mean_y = float((w * y_values).sum())
    dev_x = x_values - mean_x
    dev_y = y_values - mean_y
    covariance = float((w * dev_x * dev_y).sum())
    variance_x = float((w * dev_x**2).sum())
    variance_y = float((w * dev_y**2).sum())

    if variance_x == 0 or variance_y == 0:
        return np.nan

    return covariance / np.sqrt(variance_x * variance_y)


def weighted_spearman_correlation(
    x: pd.Series,
    y: pd.Series,
    weights: pd.Series,
) -> float:
    """Compute weighted Spearman correlation via weighted Pearson of ranks."""
    return weighted_pearson_correlation(
        x.rank(method="average"),
        y.rank(method="average"),
        weights,
    )


def _weighted_summary_row(
    group: pd.DataFrame,
    patient: str,
    cell_type: str,
    weight_method: str,
) -> dict:
    weights = compute_clone_weights(group, method=weight_method)
    return {
        "patient": patient,
        "cell_type": cell_type,
        "weight_method": weight_method,
        "n_clones": len(group),
        "weight_sum": float(weights.sum()),
        "weighted_spearman_fraction": weighted_spearman_correlation(
            group["blood_fraction"], group["sf_fraction"], weights
        ),
        "weighted_spearman_rank": weighted_pearson_correlation(
            group["blood_rank"].astype(float),
            group["sf_rank"].astype(float),
            weights,
        ),
    }


def summarize_weighted_rank_correlation(
    rank_df: pd.DataFrame,
    weight_method: str = DEFAULT_WEIGHT_METHOD,
) -> pd.DataFrame:
    """Summarize weighted Spearman correlations per patient and globally."""
    records: list[dict] = []
    for (patient, cell_type), group in rank_df.groupby(
        ["patient", "cell_type"], dropna=False
    ):
        records.append(
            _weighted_summary_row(group, str(patient), str(cell_type), weight_method)
        )

    for cell_type, group in rank_df.groupby("cell_type", dropna=False):
        records.append(_weighted_summary_row(group, "ALL", str(cell_type), weight_method))

    if not records:
        return pd.DataFrame(columns=WEIGHTED_SUMMARY_COLUMNS)
    return pd.DataFrame(records)[WEIGHTED_SUMMARY_COLUMNS]


def add_weighted_columns_to_correlation_summary(
    rank_df: pd.DataFrame,
    correlation_df: pd.DataFrame,
    weight_method: str = DEFAULT_WEIGHT_METHOD,
) -> pd.DataFrame:
    """Add weighted Spearman columns to an existing rank correlation summary."""
    weighted = summarize_weighted_rank_correlation(rank_df, weight_method=weight_method)
    weighted_subset = weighted[
        ["patient", "cell_type", "weighted_spearman_fraction", "weighted_spearman_rank"]
    ]
    result = correlation_df.merge(weighted_subset, on=["patient", "cell_type"], how="left")
    return result


def plot_weighted_spearman_by_cell_type(
    summary_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot weighted Spearman fraction by cell type and weight method."""
    plot_df = summary_df.loc[summary_df["patient"] == "ALL"].copy()
    fig, ax = plt.subplots(figsize=(8, 5))

    if plot_df.empty:
        ax.set_title("Weighted Spearman by cell type")
        ax.set_ylim(-1, 1)
    else:
        cell_types = sorted(plot_df["cell_type"].unique())
        methods = sorted(plot_df["weight_method"].unique())
        x_positions = np.arange(len(cell_types))
        bar_width = 0.8 / max(len(methods), 1)

        for index, method in enumerate(methods):
            method_df = plot_df.loc[plot_df["weight_method"] == method]
            values = [
                method_df.loc[method_df["cell_type"] == cell_type, "weighted_spearman_fraction"].iloc[0]
                if not method_df.loc[method_df["cell_type"] == cell_type].empty
                else np.nan
                for cell_type in cell_types
            ]
            offsets = x_positions + (index - (len(methods) - 1) / 2) * bar_width
            ax.bar(offsets, values, width=bar_width, label=method)

        ax.set_xticks(x_positions, cell_types)
        ax.set_ylim(-1, 1)
        ax.set_xlabel("cell_type")
        ax.set_ylabel("weighted_spearman_fraction")
        ax.set_title("Weighted Spearman fraction by cell type")
        ax.legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_clone_weight_distribution(
    rank_df: pd.DataFrame,
    weight_method: str,
    output_path: Path,
) -> None:
    """Plot histogram of clone weights for the selected weighting method."""
    weights = compute_clone_weights(rank_df, method=weight_method)
    fig, ax = plt.subplots(figsize=(7, 5))
    if weights.empty:
        ax.set_title(f"Clone weight distribution ({weight_method})")
    else:
        positive_weights = weights.loc[weights > 0]
        if positive_weights.empty:
            ax.text(0.5, 0.5, "No positive clone weights", ha="center", va="center")
        else:
            ax.hist(positive_weights, bins=30, alpha=0.8)
        ax.set_xlabel("clone weight")
        ax.set_ylabel("count")
        ax.set_title(f"Clone weight distribution ({weight_method})")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def load_rank_table(input_path: Path) -> pd.DataFrame:
    """Load rank table or build it from paired detection data."""
    df = pd.read_csv(input_path)
    if "blood_rank" in df.columns and "sf_rank" in df.columns:
        return df
    ranked = compute_clone_ranks(df)
    return compute_percentiles(ranked)


def run_weighted_rank_concordance(
    input_path: Path,
    output_dir: Path,
    weight_method: str = DEFAULT_WEIGHT_METHOD,
    cell_type: str | None = None,
    make_plots: bool = True,
) -> pd.DataFrame:
    """Run weighted rank concordance analysis and write outputs."""
    rank_df = load_rank_table(input_path)
    if cell_type is not None:
        rank_df = rank_df.loc[rank_df["cell_type"] == cell_type].copy()

    summary = summarize_weighted_rank_correlation(rank_df, weight_method=weight_method)

    out_dir = output_dir / OUTPUT_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_dir / "weighted_rank_correlation_summary.csv", index=False)

    rank_corr_path = output_dir / "rank_concordance" / "rank_correlation_summary.csv"
    if rank_corr_path.exists():
        correlation_df = pd.read_csv(rank_corr_path)
        enriched = add_weighted_columns_to_correlation_summary(
            rank_df, correlation_df, weight_method=weight_method
        )
        enriched.to_csv(rank_corr_path, index=False)

    if make_plots:
        plot_weighted_spearman_by_cell_type(
            summary, out_dir / "weighted_spearman_by_cell_type.png"
        )
        plot_clone_weight_distribution(
            rank_df, weight_method, out_dir / "clone_weight_distribution.png"
        )

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze weighted Spearman rank concordance between SF and blood."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to rank_table.csv or paired_detection_table.csv.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Base output directory.",
    )
    parser.add_argument(
        "--weight-method",
        choices=sorted(WEIGHT_METHODS),
        default=DEFAULT_WEIGHT_METHOD,
        help="Clone weighting strategy.",
    )
    parser.add_argument(
        "--cell-type",
        default=None,
        help="Keep only the specified cell type.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Write CSV outputs only, without PNG plots.",
    )
    args = parser.parse_args()
    run_weighted_rank_concordance(
        input_path=args.input,
        output_dir=args.output_dir,
        weight_method=args.weight_method,
        cell_type=args.cell_type,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
