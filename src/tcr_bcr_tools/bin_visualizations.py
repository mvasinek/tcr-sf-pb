"""Bin-level target abundance summaries and visualizations."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from tcr_bcr_tools.clone_bins import CLONE_SIZE_BINS, assign_clone_size_bin

TARGET_ABUNDANCE_SUMMARY_COLUMNS = [
    "direction",
    "cell_type",
    "bin_label",
    "bin_min",
    "bin_max",
    "n_source_clones",
    "n_target_detected",
    "detection_probability",
    "mean_target_cells_all",
    "median_target_cells_all",
    "mean_target_cells_detected_only",
    "median_target_cells_detected_only",
    "min_target_cells_detected_only",
    "max_target_cells_detected_only",
    "q25_target_cells_detected_only",
    "q75_target_cells_detected_only",
    "mean_target_fraction_detected_only",
    "median_target_fraction_detected_only",
]

BIN_SUMMARY_FILENAME = "target_abundance_summary.csv"
SCATTER_FILENAME = "scatter_target_counts.png"
BOXPLOT_FILENAME = "boxplot_target_counts.png"


def _add_bin_columns(points_df: pd.DataFrame) -> pd.DataFrame:
    enriched = points_df.copy()
    if enriched.empty:
        enriched["bin_label"] = pd.Series(dtype=str)
        enriched["bin_min"] = pd.Series(dtype=int)
        enriched["bin_max"] = pd.Series(dtype="Int64")
        return enriched

    bin_info = enriched["source_cells"].map(assign_clone_size_bin)
    enriched["bin_label"] = bin_info.map(lambda item: item[0])
    enriched["bin_min"] = bin_info.map(lambda item: item[1])
    enriched["bin_max"] = bin_info.map(lambda item: item[2])
    return enriched


def _summarize_target_group(group: pd.DataFrame) -> pd.Series:
    detected = group.loc[group["target_detected"] == True]  # noqa: E712
    n_source = len(group)
    n_detected = len(detected)

    result = {
        "n_source_clones": n_source,
        "n_target_detected": n_detected,
        "detection_probability": n_detected / n_source if n_source else 0.0,
        "mean_target_cells_all": group["target_cells"].mean(),
        "median_target_cells_all": group["target_cells"].median(),
    }

    if detected.empty:
        result.update(
            {
                "mean_target_cells_detected_only": pd.NA,
                "median_target_cells_detected_only": pd.NA,
                "min_target_cells_detected_only": pd.NA,
                "max_target_cells_detected_only": pd.NA,
                "q25_target_cells_detected_only": pd.NA,
                "q75_target_cells_detected_only": pd.NA,
                "mean_target_fraction_detected_only": pd.NA,
                "median_target_fraction_detected_only": pd.NA,
            }
        )
        return pd.Series(result)

    target_cells = detected["target_cells"]
    result.update(
        {
            "mean_target_cells_detected_only": target_cells.mean(),
            "median_target_cells_detected_only": target_cells.median(),
            "min_target_cells_detected_only": target_cells.min(),
            "max_target_cells_detected_only": target_cells.max(),
            "q25_target_cells_detected_only": target_cells.quantile(0.25),
            "q75_target_cells_detected_only": target_cells.quantile(0.75),
            "mean_target_fraction_detected_only": detected["target_fraction"].mean(),
            "median_target_fraction_detected_only": detected["target_fraction"].median(),
        }
    )
    return pd.Series(result)


def summarize_target_abundance_by_bin(points_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize target clone abundance by direction, cell type, and source bin."""
    enriched = _add_bin_columns(points_df)
    if enriched.empty:
        return pd.DataFrame(columns=TARGET_ABUNDANCE_SUMMARY_COLUMNS)

    group_columns = ["direction", "cell_type", "bin_label", "bin_min", "bin_max"]
    records: list[dict] = []
    for key, group in enriched.groupby(group_columns, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        record = dict(zip(group_columns, key))
        record.update(_summarize_target_group(group).to_dict())
        records.append(record)

    summary = pd.DataFrame(records)
    summary["n_target_detected"] = summary["n_target_detected"].astype(int)
    return summary.sort_values(["direction", "cell_type", "bin_min"])[
        TARGET_ABUNDANCE_SUMMARY_COLUMNS
    ]


def get_bin_points(
    points_df: pd.DataFrame,
    direction: str,
    bin_label: str,
    cell_type: str | None = None,
    detected_only: bool = False,
) -> pd.DataFrame:
    """Return detection points for one direction and source clone-size bin."""
    enriched = _add_bin_columns(points_df)
    mask = (enriched["direction"] == direction) & (enriched["bin_label"] == bin_label)
    if cell_type is not None:
        mask &= enriched["cell_type"] == cell_type
    if detected_only:
        mask &= enriched["target_detected"] == True  # noqa: E712
    return enriched.loc[mask].copy()


def _format_plot_title(
    direction: str, bin_label: str, cell_type: str | None = None
) -> str:
    cell_label = cell_type if cell_type is not None else "all"
    return f"{direction} | {cell_label} | source bin {bin_label}"


def plot_bin_scatter(
    bin_df: pd.DataFrame,
    direction: str,
    bin_label: str,
    output_path: Path,
    cell_type: str | None = None,
) -> None:
    """Plot source vs target clone counts for one bin."""
    fig, ax = plt.subplots(figsize=(7, 5))
    if not bin_df.empty:
        ax.scatter(bin_df["source_cells"], bin_df["target_cells"], alpha=0.7)
    ax.set_xlabel("source_cells")
    ax.set_ylabel("target_cells")
    ax.set_title(_format_plot_title(direction, bin_label, cell_type))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_bin_boxplot(
    bin_df: pd.DataFrame,
    direction: str,
    bin_label: str,
    output_path: Path,
    cell_type: str | None = None,
    detected_only: bool = True,
) -> None:
    """Plot target clone counts for one bin as a boxplot."""
    fig, ax = plt.subplots(figsize=(6, 5))
    plot_df = bin_df
    if detected_only:
        plot_df = bin_df.loc[bin_df["target_detected"] == True]  # noqa: E712

    if plot_df.empty:
        ax.text(
            0.5,
            0.5,
            "No detected target clones in this bin",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_xticks([])
        ax.set_ylabel("target_cells")
    else:
        ax.boxplot(plot_df["target_cells"].tolist())
        ax.set_xticklabels(["detected"])
        ax.set_ylabel("target_cells")

    ax.set_title(_format_plot_title(direction, bin_label, cell_type))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def export_bin_visualizations(
    points_df: pd.DataFrame,
    output_dir: Path,
    cell_type: str | None = None,
    global_summary_path: Path | None = None,
) -> pd.DataFrame:
    """Export per-bin target abundance summaries and plots."""
    filtered_points = points_df.copy()
    if cell_type is not None:
        filtered_points = filtered_points.loc[
            filtered_points["cell_type"] == cell_type
        ].copy()

    summary = summarize_target_abundance_by_bin(filtered_points)
    if global_summary_path is not None:
        global_summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(global_summary_path, index=False)

    enriched = _add_bin_columns(filtered_points)
    if enriched.empty:
        return summary

    bin_keys = (
        enriched[["direction", "bin_label"]]
        .drop_duplicates()
        .sort_values(["direction", "bin_label"])
    )

    for row in bin_keys.itertuples(index=False):
        direction = row.direction
        bin_label = row.bin_label
        bin_dir = output_dir / direction / bin_label
        bin_dir.mkdir(parents=True, exist_ok=True)
        bin_points = get_bin_points(
            filtered_points,
            direction=direction,
            bin_label=bin_label,
            cell_type=cell_type,
        )
        bin_summary = summarize_target_abundance_by_bin(bin_points)
        bin_summary.to_csv(bin_dir / BIN_SUMMARY_FILENAME, index=False)
        plot_bin_scatter(
            bin_points,
            direction=direction,
            bin_label=bin_label,
            output_path=bin_dir / SCATTER_FILENAME,
            cell_type=cell_type,
        )
        plot_bin_boxplot(
            bin_points,
            direction=direction,
            bin_label=bin_label,
            output_path=bin_dir / BOXPLOT_FILENAME,
            cell_type=cell_type,
        )

    return summary


def all_bin_labels() -> list[str]:
    """Return all configured clone-size bin labels in order."""
    return [label for label, _, _ in CLONE_SIZE_BINS]
