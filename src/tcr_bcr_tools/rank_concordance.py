"""Rank and percentile concordance analysis between SF and blood."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RANK_TABLE_COLUMNS = [
    "patient",
    "cell_type",
    "clonotype_key",
    "blood_cells",
    "sf_cells",
    "blood_fraction",
    "sf_fraction",
    "blood_rank",
    "sf_rank",
    "blood_percentile",
    "sf_percentile",
]

RANK_CORRELATION_COLUMNS = [
    "patient",
    "cell_type",
    "pearson_fraction",
    "spearman_fraction",
    "kendall_fraction",
    "pearson_rank",
    "spearman_rank",
    "kendall_rank",
    "weighted_spearman_fraction",
    "weighted_spearman_rank",
    "n_clones",
]

PERCENTILE_CONCORDANCE_COLUMNS = [
    "cell_type",
    "percentile_threshold",
    "n_sf_top",
    "n_blood_top",
    "n_top_both",
    "p_sf_top_given_blood_top",
    "p_blood_top_given_sf_top",
    "jaccard_top",
]

TOP_OVERLAP_COLUMNS = [
    "cell_type",
    "top_n",
    "blood_overlap",
    "sf_overlap",
    "jaccard_overlap",
]

PERCENTILE_THRESHOLDS = [0.50, 0.75, 0.90, 0.95, 0.99]
TOP_N_VALUES = [1, 3, 5, 10, 20, 50, 100]
OUTPUT_DIRNAME = "rank_concordance"


def _rank_within_group(
    group: pd.DataFrame, fraction_col: str, cells_col: str
) -> pd.Series:
    ordered = group.sort_values(
        [fraction_col, cells_col, "clonotype_key"],
        ascending=[False, False, True],
    )
    return pd.Series(range(1, len(ordered) + 1), index=ordered.index, dtype=int)


def _percentile_from_rank(rank: pd.Series, group_size: int) -> pd.Series:
    if group_size == 0:
        return rank.astype(float)
    if group_size == 1:
        return pd.Series(1.0, index=rank.index)
    return (group_size - rank + 1) / group_size


def compute_clone_ranks(df: pd.DataFrame) -> pd.DataFrame:
    """Assign deterministic blood and SF ranks within patient and cell type."""
    result = df.copy()
    result["blood_rank"] = pd.NA
    result["sf_rank"] = pd.NA

    for _, group in result.groupby(["patient", "cell_type"], dropna=False):
        blood_ranks = _rank_within_group(group, "blood_fraction", "blood_cells")
        sf_ranks = _rank_within_group(group, "sf_fraction", "sf_cells")
        result.loc[blood_ranks.index, "blood_rank"] = blood_ranks
        result.loc[sf_ranks.index, "sf_rank"] = sf_ranks

    result["blood_rank"] = result["blood_rank"].astype(int)
    result["sf_rank"] = result["sf_rank"].astype(int)
    return result


def compute_percentiles(rank_df: pd.DataFrame) -> pd.DataFrame:
    """Compute blood and SF percentiles where 1.0 is the largest clone."""
    result = rank_df.copy()
    result["blood_percentile"] = np.nan
    result["sf_percentile"] = np.nan

    for _, group in result.groupby(["patient", "cell_type"], dropna=False):
        group_size = len(group)
        result.loc[group.index, "blood_percentile"] = _percentile_from_rank(
            group["blood_rank"], group_size
        )
        result.loc[group.index, "sf_percentile"] = _percentile_from_rank(
            group["sf_rank"], group_size
        )

    return result[RANK_TABLE_COLUMNS].copy()


def _correlation_value(
    x: pd.Series, y: pd.Series, method: str
) -> float:
    if len(x) < 2:
        return np.nan
    if x.nunique() <= 1 or y.nunique() <= 1:
        return np.nan
    return float(x.corr(y, method=method))


def _correlation_row(group: pd.DataFrame, patient: str, cell_type: str) -> dict:
    return {
        "patient": patient,
        "cell_type": cell_type,
        "pearson_fraction": _correlation_value(
            group["blood_fraction"], group["sf_fraction"], "pearson"
        ),
        "spearman_fraction": _correlation_value(
            group["blood_fraction"], group["sf_fraction"], "spearman"
        ),
        "kendall_fraction": _correlation_value(
            group["blood_fraction"], group["sf_fraction"], "kendall"
        ),
        "pearson_rank": _correlation_value(
            group["blood_rank"], group["sf_rank"], "pearson"
        ),
        "spearman_rank": _correlation_value(
            group["blood_rank"], group["sf_rank"], "spearman"
        ),
        "kendall_rank": _correlation_value(
            group["blood_rank"], group["sf_rank"], "kendall"
        ),
        "n_clones": len(group),
    }


def compute_rank_correlations(
    rank_df: pd.DataFrame,
    weight_method: str = "max_fraction",
) -> pd.DataFrame:
    """Compute fraction and rank correlations per patient and globally."""
    from tcr_bcr_tools.weighted_rank_concordance import (
        add_weighted_columns_to_correlation_summary,
    )

    records: list[dict] = []
    for (patient, cell_type), group in rank_df.groupby(
        ["patient", "cell_type"], dropna=False
    ):
        records.append(_correlation_row(group, str(patient), str(cell_type)))

    for cell_type, group in rank_df.groupby("cell_type", dropna=False):
        records.append(_correlation_row(group, "ALL", str(cell_type)))

    if not records:
        return pd.DataFrame(columns=RANK_CORRELATION_COLUMNS)

    summary = pd.DataFrame(records)
    return add_weighted_columns_to_correlation_summary(
        rank_df, summary, weight_method=weight_method
    )[RANK_CORRELATION_COLUMNS]


def _top_set_metrics(
    sf_top: pd.Series, blood_top: pd.Series
) -> dict[str, float | int]:
    n_sf_top = int(sf_top.sum())
    n_blood_top = int(blood_top.sum())
    n_top_both = int((sf_top & blood_top).sum())
    union = n_sf_top + n_blood_top - n_top_both

    return {
        "n_sf_top": n_sf_top,
        "n_blood_top": n_blood_top,
        "n_top_both": n_top_both,
        "p_sf_top_given_blood_top": (
            n_top_both / n_blood_top if n_blood_top > 0 else np.nan
        ),
        "p_blood_top_given_sf_top": (
            n_top_both / n_sf_top if n_sf_top > 0 else np.nan
        ),
        "jaccard_top": n_top_both / union if union > 0 else np.nan,
    }


def compute_percentile_concordance(rank_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize percentile concordance at fixed top-percentile thresholds."""
    records: list[dict] = []
    for cell_type, group in rank_df.groupby("cell_type", dropna=False):
        for threshold in PERCENTILE_THRESHOLDS:
            sf_top = group["sf_percentile"] >= threshold
            blood_top = group["blood_percentile"] >= threshold
            record = {
                "cell_type": cell_type,
                "percentile_threshold": threshold,
            }
            record.update(_top_set_metrics(sf_top, blood_top))
            records.append(record)

    if not records:
        return pd.DataFrame(columns=PERCENTILE_CONCORDANCE_COLUMNS)
    return pd.DataFrame(records)[PERCENTILE_CONCORDANCE_COLUMNS]


def _top_overlap_metrics(
    group: pd.DataFrame, top_n: int
) -> dict[str, float]:
    blood_top = group.loc[group["blood_rank"] <= top_n, "clonotype_key"]
    sf_top = group.loc[group["sf_rank"] <= top_n, "clonotype_key"]
    blood_set = set(blood_top)
    sf_set = set(sf_top)
    intersection = blood_set & sf_set
    union = blood_set | sf_set

    blood_overlap = len(intersection) / len(blood_set) if blood_set else np.nan
    sf_overlap = len(intersection) / len(sf_set) if sf_set else np.nan
    jaccard_overlap = len(intersection) / len(union) if union else np.nan

    return {
        "blood_overlap": blood_overlap,
        "sf_overlap": sf_overlap,
        "jaccard_overlap": jaccard_overlap,
    }


def compute_top_overlap(rank_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize Top-N clone overlap between blood and SF."""
    records: list[dict] = []
    for cell_type, group in rank_df.groupby("cell_type", dropna=False):
        for top_n in TOP_N_VALUES:
            record = {"cell_type": cell_type, "top_n": top_n}
            record.update(_top_overlap_metrics(group, top_n))
            records.append(record)

    if not records:
        return pd.DataFrame(columns=TOP_OVERLAP_COLUMNS)
    return pd.DataFrame(records)[TOP_OVERLAP_COLUMNS]


def plot_rank_scatter(rank_df: pd.DataFrame, output_path: Path) -> None:
    """Plot SF percentile vs blood percentile with y=x reference."""
    fig, ax = plt.subplots(figsize=(7, 6))
    if not rank_df.empty:
        ax.scatter(
            rank_df["blood_percentile"],
            rank_df["sf_percentile"],
            alpha=0.4,
            s=10,
        )
        ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="y=x")
        ax.legend()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("blood_percentile")
    ax.set_ylabel("sf_percentile")
    ax.set_title("SF vs blood clone percentiles")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _percentile_decile(percentile: pd.Series) -> pd.Series:
    values = percentile.to_numpy(dtype=float)
    deciles = np.clip(np.floor(values * 10 - 1e-12), 0, 9).astype(int)
    return pd.Series(deciles, index=percentile.index)


def plot_percentile_heatmap(rank_df: pd.DataFrame, output_path: Path) -> None:
    """Plot a 10x10 decile heatmap of blood vs SF percentiles."""
    fig, ax = plt.subplots(figsize=(8, 7))
    if rank_df.empty:
        ax.set_title("Percentile decile heatmap")
    else:
        blood_decile = _percentile_decile(rank_df["blood_percentile"])
        sf_decile = _percentile_decile(rank_df["sf_percentile"])
        matrix = np.zeros((10, 10), dtype=int)
        for blood_bin, sf_bin in zip(blood_decile, sf_decile, strict=True):
            matrix[int(sf_bin), int(blood_bin)] += 1

        image = ax.imshow(matrix, origin="lower", aspect="auto", cmap="Blues")
        ax.set_xticks(range(10), [f"{i*10}-{(i+1)*10}" for i in range(10)])
        ax.set_yticks(range(10), [f"{i*10}-{(i+1)*10}" for i in range(10)])
        ax.set_xlabel("blood percentile decile")
        ax.set_ylabel("SF percentile decile")
        ax.set_title("Percentile decile heatmap")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_top_overlap_curve(overlap_df: pd.DataFrame, output_path: Path) -> None:
    """Plot Top-N overlap probabilities."""
    fig, ax = plt.subplots(figsize=(8, 5))
    if overlap_df.empty:
        ax.set_title("Top-N overlap")
        ax.set_ylim(0, 1)
    else:
        for cell_type, group in overlap_df.groupby("cell_type", dropna=False):
            ordered = group.sort_values("top_n")
            ax.plot(
                ordered["top_n"],
                ordered["blood_overlap"],
                marker="o",
                label=f"{cell_type}: P(top N SF | top N blood)",
            )
            ax.plot(
                ordered["top_n"],
                ordered["sf_overlap"],
                marker="s",
                linestyle="--",
                label=f"{cell_type}: P(top N blood | top N SF)",
            )
        ax.set_xscale("log")
        ax.set_ylim(0, 1)
        ax.set_xlabel("Top N")
        ax.set_ylabel("overlap probability")
        ax.set_title("Top-N overlap between SF and blood")
        ax.legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run_rank_concordance(
    input_path: Path,
    output_dir: Path,
    cell_type: str | None = None,
    make_plots: bool = True,
) -> None:
    """Run rank and percentile concordance analysis."""
    df = pd.read_csv(input_path)
    if cell_type is not None:
        df = df.loc[df["cell_type"] == cell_type].copy()

    ranked = compute_clone_ranks(df)
    rank_table = compute_percentiles(ranked)
    correlation_summary = compute_rank_correlations(rank_table)
    percentile_summary = compute_percentile_concordance(rank_table)
    overlap_summary = compute_top_overlap(rank_table)

    out_dir = output_dir / OUTPUT_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    rank_table.to_csv(out_dir / "rank_table.csv", index=False)
    correlation_summary.to_csv(out_dir / "rank_correlation_summary.csv", index=False)
    percentile_summary.to_csv(out_dir / "percentile_concordance_summary.csv", index=False)
    overlap_summary.to_csv(out_dir / "top_overlap_summary.csv", index=False)

    if make_plots:
        plot_rank_scatter(rank_table, out_dir / "rank_scatter.png")
        plot_percentile_heatmap(rank_table, out_dir / "percentile_heatmap.png")
        plot_top_overlap_curve(overlap_summary, out_dir / "top_overlap_curve.png")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze rank and percentile concordance between SF and blood."
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
        help="Base output directory (files go to {output_dir}/rank_concordance/).",
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
    run_rank_concordance(
        input_path=args.input,
        output_dir=args.output_dir,
        cell_type=args.cell_type,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
