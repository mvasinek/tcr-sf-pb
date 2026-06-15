"""Decile heatmap and information metrics between blood and SF clone sizes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    adjusted_mutual_info_score,
    mutual_info_score,
    normalized_mutual_info_score,
)

from tcr_bcr_tools.rank_concordance import compute_clone_ranks, compute_percentiles

DEFAULT_N_BINS = 10
OUTPUT_DIRNAME = "decile_information"
LN2 = np.log(2)

DECILE_TABLE_COLUMNS = [
    "patient",
    "cell_type",
    "clonotype_key",
    "blood_cells",
    "sf_cells",
    "blood_fraction",
    "sf_fraction",
    "blood_decile",
    "sf_decile",
    "blood_percentile",
    "sf_percentile",
    "shared_clone",
]

TRANSITION_MATRIX_COLUMNS = [
    "cell_type",
    "blood_decile",
    "sf_decile",
    "n_clones",
    "fraction_of_blood_decile",
    "fraction_of_all_clones",
]

INFORMATION_METRICS_COLUMNS = [
    "cell_type",
    "n_clones",
    "mutual_information",
    "normalized_mutual_information",
    "adjusted_mutual_information",
    "entropy_blood",
    "entropy_sf",
    "conditional_entropy_sf_given_blood",
    "conditional_entropy_blood_given_sf",
    "uncertainty_reduction_sf_given_blood",
    "uncertainty_reduction_blood_given_sf",
]

TOP_DECILE_ENRICHMENT_COLUMNS = [
    "cell_type",
    "blood_top_decile",
    "sf_top_decile",
    "n_blood_top",
    "n_sf_top",
    "n_both_top",
    "p_sf_top_given_blood_top",
    "p_blood_top_given_sf_top",
    "enrichment_vs_random",
    "odds_ratio",
]

HALDANE_ANSCOMBE_CORRECTION = 0.5


def _bin_from_percentile(percentile: pd.Series, n_bins: int) -> pd.Series:
    values = percentile.to_numpy(dtype=float)
    bins = np.clip(np.ceil(values * n_bins), 1, n_bins).astype(int)
    return pd.Series(bins, index=percentile.index)


def _ensure_percentiles(
    df: pd.DataFrame,
    rank_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if {"blood_percentile", "sf_percentile"}.issubset(df.columns):
        return df.copy()

    if rank_df is not None:
        rank_cols = [
            "patient",
            "cell_type",
            "clonotype_key",
            "blood_percentile",
            "sf_percentile",
        ]
        if set(rank_cols).issubset(rank_df.columns):
            return df.merge(
                rank_df[rank_cols],
                on=["patient", "cell_type", "clonotype_key"],
                how="left",
            )

    rank_table = compute_percentiles(compute_clone_ranks(df))
    return df.merge(
        rank_table[
            ["patient", "cell_type", "clonotype_key", "blood_percentile", "sf_percentile"]
        ],
        on=["patient", "cell_type", "clonotype_key"],
        how="left",
    )


def assign_compartment_bins(
    df: pd.DataFrame,
    n_bins: int = DEFAULT_N_BINS,
    rank_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Assign blood and SF size bins within each patient and cell type."""
    if n_bins < 1:
        raise ValueError("n_bins must be at least 1.")

    with_percentiles = _ensure_percentiles(df, rank_df=rank_df)
    result = with_percentiles.copy()
    result["blood_decile"] = _bin_from_percentile(result["blood_percentile"], n_bins)
    result["sf_decile"] = _bin_from_percentile(result["sf_percentile"], n_bins)

    available = [col for col in DECILE_TABLE_COLUMNS if col in result.columns]
    return result[available].copy()


def build_transition_matrix(
    binned_df: pd.DataFrame,
    n_bins: int = DEFAULT_N_BINS,
) -> pd.DataFrame:
    """Build long-form blood-to-SF transition matrix per cell type."""
    records: list[dict] = []

    for cell_type, group in binned_df.groupby("cell_type", dropna=False):
        cell_type_str = str(cell_type)
        total_clones = len(group)
        blood_totals = group.groupby("blood_decile").size().to_dict()

        for blood_decile in range(1, n_bins + 1):
            blood_group = group.loc[group["blood_decile"] == blood_decile]
            blood_count = int(blood_totals.get(blood_decile, 0))

            for sf_decile in range(1, n_bins + 1):
                n_clones = int((blood_group["sf_decile"] == sf_decile).sum())
                records.append(
                    {
                        "cell_type": cell_type_str,
                        "blood_decile": blood_decile,
                        "sf_decile": sf_decile,
                        "n_clones": n_clones,
                        "fraction_of_blood_decile": (
                            n_clones / blood_count if blood_count > 0 else np.nan
                        ),
                        "fraction_of_all_clones": (
                            n_clones / total_clones if total_clones > 0 else np.nan
                        ),
                    }
                )

    return pd.DataFrame(records)[TRANSITION_MATRIX_COLUMNS]


def entropy_from_labels(labels: pd.Series) -> float:
    """Compute Shannon entropy in bits (base-2)."""
    values = labels.dropna()
    if values.empty:
        return np.nan

    counts = values.value_counts(normalize=True)
    probabilities = counts.to_numpy()
    probabilities = probabilities[probabilities > 0]
    if len(probabilities) <= 1:
        return 0.0
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _mutual_information_bits(x: pd.Series, y: pd.Series) -> float:
    return float(mutual_info_score(x, y) / LN2)


def compute_information_metrics(
    binned_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute information-theoretic metrics per cell type."""
    records: list[dict] = []

    for cell_type, group in binned_df.groupby("cell_type", dropna=False):
        n_clones = len(group)
        nan_row = {
            "cell_type": str(cell_type),
            "n_clones": n_clones,
            "mutual_information": np.nan,
            "normalized_mutual_information": np.nan,
            "adjusted_mutual_information": np.nan,
            "entropy_blood": np.nan,
            "entropy_sf": np.nan,
            "conditional_entropy_sf_given_blood": np.nan,
            "conditional_entropy_blood_given_sf": np.nan,
            "uncertainty_reduction_sf_given_blood": np.nan,
            "uncertainty_reduction_blood_given_sf": np.nan,
        }

        if n_clones < 3:
            records.append(nan_row)
            continue

        blood = group["blood_decile"]
        sf = group["sf_decile"]
        entropy_blood = entropy_from_labels(blood)
        entropy_sf = entropy_from_labels(sf)
        mutual_information = _mutual_information_bits(blood, sf)

        records.append(
            {
                "cell_type": str(cell_type),
                "n_clones": n_clones,
                "mutual_information": mutual_information,
                "normalized_mutual_information": float(
                    normalized_mutual_info_score(blood, sf)
                ),
                "adjusted_mutual_information": float(
                    adjusted_mutual_info_score(blood, sf)
                ),
                "entropy_blood": entropy_blood,
                "entropy_sf": entropy_sf,
                "conditional_entropy_sf_given_blood": entropy_sf - mutual_information,
                "conditional_entropy_blood_given_sf": entropy_blood - mutual_information,
                "uncertainty_reduction_sf_given_blood": (
                    mutual_information / entropy_sf if entropy_sf > 0 else np.nan
                ),
                "uncertainty_reduction_blood_given_sf": (
                    mutual_information / entropy_blood if entropy_blood > 0 else np.nan
                ),
            }
        )

    if not records:
        return pd.DataFrame(columns=INFORMATION_METRICS_COLUMNS)
    return pd.DataFrame(records)[INFORMATION_METRICS_COLUMNS]


def _haldane_odds_ratio(
    both_top: int,
    blood_top_sf_not: int,
    blood_not_sf_top: int,
    neither_top: int,
) -> float:
    correction = HALDANE_ANSCOMBE_CORRECTION
    numerator = (both_top + correction) * (neither_top + correction)
    denominator = (blood_top_sf_not + correction) * (blood_not_sf_top + correction)
    return float(numerator / denominator)


def compute_top_bin_enrichment(
    binned_df: pd.DataFrame,
    n_bins: int = DEFAULT_N_BINS,
) -> pd.DataFrame:
    """Compute top-bin enrichment between blood and SF compartments."""
    records: list[dict] = []

    for cell_type, group in binned_df.groupby("cell_type", dropna=False):
        n_clones = len(group)
        blood_top = group["blood_decile"] == n_bins
        sf_top = group["sf_decile"] == n_bins
        n_blood_top = int(blood_top.sum())
        n_sf_top = int(sf_top.sum())
        n_both_top = int((blood_top & sf_top).sum())
        baseline_p_sf_top = n_sf_top / n_clones if n_clones > 0 else np.nan
        p_sf_given_blood = (
            n_both_top / n_blood_top if n_blood_top > 0 else np.nan
        )
        p_blood_given_sf = n_both_top / n_sf_top if n_sf_top > 0 else np.nan
        enrichment = (
            p_sf_given_blood / baseline_p_sf_top
            if baseline_p_sf_top and baseline_p_sf_top > 0 and not np.isnan(p_sf_given_blood)
            else np.nan
        )

        blood_top_sf_not = n_blood_top - n_both_top
        blood_not_sf_top = n_sf_top - n_both_top
        neither_top = n_clones - n_blood_top - n_sf_top + n_both_top

        records.append(
            {
                "cell_type": str(cell_type),
                "blood_top_decile": True,
                "sf_top_decile": True,
                "n_blood_top": n_blood_top,
                "n_sf_top": n_sf_top,
                "n_both_top": n_both_top,
                "p_sf_top_given_blood_top": p_sf_given_blood,
                "p_blood_top_given_sf_top": p_blood_given_sf,
                "enrichment_vs_random": enrichment,
                "odds_ratio": _haldane_odds_ratio(
                    n_both_top,
                    blood_top_sf_not,
                    blood_not_sf_top,
                    neither_top,
                ),
            }
        )

    if not records:
        return pd.DataFrame(columns=TOP_DECILE_ENRICHMENT_COLUMNS)
    return pd.DataFrame(records)[TOP_DECILE_ENRICHMENT_COLUMNS]


def _matrix_grid(
    matrix_df: pd.DataFrame,
    cell_type: str,
    value_col: str,
    n_bins: int,
) -> np.ndarray:
    cell_matrix = matrix_df.loc[matrix_df["cell_type"] == cell_type]
    grid = np.zeros((n_bins, n_bins), dtype=float)

    for _, row in cell_matrix.iterrows():
        blood_idx = int(row["blood_decile"]) - 1
        sf_idx = int(row["sf_decile"]) - 1
        grid[blood_idx, sf_idx] = float(row[value_col])

    return grid


def plot_decile_heatmap(
    matrix_df: pd.DataFrame,
    cell_type: str,
    value_col: str,
    output_path: Path,
    n_bins: int = DEFAULT_N_BINS,
) -> None:
    """Plot a blood-by-SF decile heatmap for one cell type."""
    grid = _matrix_grid(matrix_df, cell_type, value_col, n_bins)
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(grid, origin="lower", aspect="auto", cmap="Blues")
    tick_labels = [str(value) for value in range(1, n_bins + 1)]
    ax.set_xticks(range(n_bins), tick_labels)
    ax.set_yticks(range(n_bins), tick_labels)
    ax.set_xlabel("sf_decile")
    ax.set_ylabel("blood_decile")
    ax.set_title(f"{cell_type}: {value_col}")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_heatmap_panels(
    matrix_df: pd.DataFrame,
    value_col: str,
    output_path: Path,
    n_bins: int,
    title: str,
) -> None:
    cell_types = sorted(matrix_df["cell_type"].dropna().unique())
    n_panels = max(len(cell_types), 1)
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 4.5), squeeze=False)

    for index, cell_type in enumerate(cell_types):
        ax = axes[0, index]
        grid = _matrix_grid(matrix_df, str(cell_type), value_col, n_bins)
        image = ax.imshow(grid, origin="lower", aspect="auto", cmap="Blues")
        tick_labels = [str(value) for value in range(1, n_bins + 1)]
        ax.set_xticks(range(n_bins), tick_labels)
        ax.set_yticks(range(n_bins), tick_labels)
        ax.set_xlabel("sf_decile")
        ax.set_ylabel("blood_decile")
        ax.set_title(str(cell_type))
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

    if not cell_types:
        axes[0, 0].set_title(title)

    fig.suptitle(title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_information_metrics(
    metrics_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot information metrics by cell type."""
    metric_columns = [
        "normalized_mutual_information",
        "uncertainty_reduction_sf_given_blood",
        "uncertainty_reduction_blood_given_sf",
    ]
    plot_df = metrics_df.dropna(subset=metric_columns, how="all").copy()
    fig, ax = plt.subplots(figsize=(9, 5))

    if plot_df.empty:
        ax.set_title("Information metrics by cell type")
    else:
        cell_types = plot_df["cell_type"].astype(str).tolist()
        x_positions = np.arange(len(cell_types))
        bar_width = 0.8 / len(metric_columns)

        for index, metric in enumerate(metric_columns):
            offsets = x_positions + (index - (len(metric_columns) - 1) / 2) * bar_width
            ax.bar(
                offsets,
                plot_df[metric].to_numpy(),
                width=bar_width,
                label=metric,
            )

        ax.set_xticks(x_positions, cell_types)
        ax.set_ylabel("value")
        ax.set_title("Information metrics by cell type")
        ax.legend(fontsize=7)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_top_decile_enrichment(
    enrichment_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot top-decile enrichment by cell type."""
    fig, ax = plt.subplots(figsize=(7, 5))

    if enrichment_df.empty:
        ax.set_title("Top decile enrichment")
    else:
        cell_types = enrichment_df["cell_type"].astype(str).tolist()
        values = enrichment_df["enrichment_vs_random"].to_numpy()
        ax.bar(cell_types, values)
        ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
        ax.set_xlabel("cell_type")
        ax.set_ylabel("enrichment_vs_random")
        ax.set_title("Top decile enrichment")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _load_optional_rank_table(output_dir: Path) -> pd.DataFrame | None:
    rank_path = output_dir / "rank_concordance" / "rank_table.csv"
    if rank_path.exists():
        return pd.read_csv(rank_path)
    return None


def run_decile_information_analysis(
    input_path: Path,
    output_dir: Path,
    cell_type: str | None = None,
    n_bins: int = DEFAULT_N_BINS,
    make_plots: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run decile information analysis and write outputs."""
    df = pd.read_csv(input_path)
    if cell_type is not None:
        df = df.loc[df["cell_type"] == cell_type].copy()

    rank_df = _load_optional_rank_table(output_dir)
    decile_table = assign_compartment_bins(df, n_bins=n_bins, rank_df=rank_df)
    transition_matrix = build_transition_matrix(decile_table, n_bins=n_bins)
    information_metrics = compute_information_metrics(decile_table)
    top_enrichment = compute_top_bin_enrichment(decile_table, n_bins=n_bins)

    out_dir = output_dir / OUTPUT_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    decile_table.to_csv(out_dir / "decile_table.csv", index=False)
    transition_matrix.to_csv(out_dir / "decile_transition_matrix.csv", index=False)
    information_metrics.to_csv(out_dir / "information_metrics_summary.csv", index=False)
    top_enrichment.to_csv(out_dir / "top_decile_enrichment.csv", index=False)

    if make_plots:
        _plot_heatmap_panels(
            transition_matrix,
            "n_clones",
            out_dir / "decile_heatmap_counts.png",
            n_bins,
            "Decile heatmap counts",
        )
        _plot_heatmap_panels(
            transition_matrix,
            "fraction_of_blood_decile",
            out_dir / "decile_heatmap_row_fraction.png",
            n_bins,
            "Decile heatmap row fraction",
        )
        plot_information_metrics(
            information_metrics,
            out_dir / "information_metrics_by_cell_type.png",
        )
        plot_top_decile_enrichment(
            top_enrichment,
            out_dir / "top_decile_enrichment.png",
        )

    return decile_table, transition_matrix, information_metrics, top_enrichment


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze decile information between blood and SF clone sizes."
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
        "--cell-type",
        default=None,
        help="Keep only the specified cell type.",
    )
    parser.add_argument(
        "--n-bins",
        type=int,
        default=DEFAULT_N_BINS,
        help="Number of size bins per compartment (default: 10).",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Write CSV outputs only, without PNG plots.",
    )
    args = parser.parse_args()
    run_decile_information_analysis(
        input_path=args.input,
        output_dir=args.output_dir,
        cell_type=args.cell_type,
        n_bins=args.n_bins,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
