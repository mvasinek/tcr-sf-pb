"""Detection curve analysis from paired SF/blood clone tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from tcr_bcr_tools.clone_bins import CLONE_SIZE_BINS, assign_clone_size_bin

POINTS_COLUMNS = [
    "direction",
    "patient",
    "cell_type",
    "clonotype_key",
    "source_cells",
    "target_cells",
    "source_fraction",
    "target_fraction",
    "target_detected",
    "shared_clone",
]

SUMMARY_COLUMNS = [
    "direction",
    "cell_type",
    "bin_label",
    "bin_min",
    "bin_max",
    "n_clones",
    "n_detected",
    "detection_probability",
    "mean_source_cells",
    "median_source_cells",
    "mean_source_fraction",
    "median_source_fraction",
]

DIRECTION_TITLES = {
    "sf_to_blood": "P(blood detected | SF clone size)",
    "blood_to_sf": "P(SF detected | blood clone size)",
}

DIRECTION_OUTPUT_FILES = {
    "sf_to_blood": "detection_curve_sf_to_blood.png",
    "blood_to_sf": "detection_curve_blood_to_sf.png",
}


def _build_direction_points(
    df: pd.DataFrame,
    direction: str,
    source_mask: pd.Series,
    mapping: dict[str, str],
) -> pd.DataFrame:
    subset = df.loc[source_mask].copy()
    if subset.empty:
        return pd.DataFrame(columns=POINTS_COLUMNS)

    points = pd.DataFrame(
        {
            "direction": direction,
            "patient": subset["patient"],
            "cell_type": subset["cell_type"],
            "clonotype_key": subset["clonotype_key"],
            "source_cells": subset[mapping["source_cells"]],
            "target_cells": subset[mapping["target_cells"]],
            "source_fraction": subset[mapping["source_fraction"]],
            "target_fraction": subset[mapping["target_fraction"]],
            "target_detected": subset[mapping["target_detected"]],
            "shared_clone": subset["shared_clone"],
        }
    )
    return points[POINTS_COLUMNS]


def build_detection_points(
    df: pd.DataFrame, min_source_cells: int = 1
) -> pd.DataFrame:
    """Create detection curve points for both analysis directions."""
    sf_to_blood = _build_direction_points(
        df,
        direction="sf_to_blood",
        source_mask=df["sf_cells"] > 0,
        mapping={
            "source_cells": "sf_cells",
            "target_cells": "blood_cells",
            "source_fraction": "sf_fraction",
            "target_fraction": "blood_fraction",
            "target_detected": "detected_in_blood",
        },
    )
    blood_to_sf = _build_direction_points(
        df,
        direction="blood_to_sf",
        source_mask=df["blood_cells"] > 0,
        mapping={
            "source_cells": "blood_cells",
            "target_cells": "sf_cells",
            "source_fraction": "blood_fraction",
            "target_fraction": "sf_fraction",
            "target_detected": "detected_in_sf",
        },
    )

    points = pd.concat([sf_to_blood, blood_to_sf], ignore_index=True)
    if points.empty:
        return pd.DataFrame(columns=POINTS_COLUMNS)

    points = points.loc[points["source_cells"] >= min_source_cells].copy()
    return points[POINTS_COLUMNS]


def summarize_detection_curve(points_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize detection probabilities by direction, cell type, and clone-size bin."""
    if points_df.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    enriched = points_df.copy()
    bin_info = enriched["source_cells"].map(assign_clone_size_bin)
    enriched["bin_label"] = bin_info.map(lambda item: item[0])
    enriched["bin_min"] = bin_info.map(lambda item: item[1])
    enriched["bin_max"] = bin_info.map(lambda item: item[2])

    summary = (
        enriched.groupby(
            ["direction", "cell_type", "bin_label", "bin_min", "bin_max"],
            as_index=False,
            dropna=False,
        )
        .agg(
            n_clones=("clonotype_key", "count"),
            n_detected=("target_detected", "sum"),
            mean_source_cells=("source_cells", "mean"),
            median_source_cells=("source_cells", "median"),
            mean_source_fraction=("source_fraction", "mean"),
            median_source_fraction=("source_fraction", "median"),
        )
        .sort_values(["direction", "cell_type", "bin_min"])
    )
    summary["detection_probability"] = summary["n_detected"] / summary["n_clones"]
    summary["n_detected"] = summary["n_detected"].astype(int)
    return summary[SUMMARY_COLUMNS]


def plot_detection_curve(
    summary_df: pd.DataFrame,
    direction: str,
    output_path: Path,
) -> None:
    """Plot empirical detection probability by clone-size bin."""
    direction_summary = summary_df.loc[summary_df["direction"] == direction].copy()
    if direction_summary.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.set_title(DIRECTION_TITLES[direction])
        ax.set_xlabel("Source clone size bin")
        ax.set_ylabel("Detection probability")
        ax.set_ylim(0, 1)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    plot_data = (
        direction_summary.groupby(["bin_label", "bin_min", "bin_max"], as_index=False)
        .agg(
            n_clones=("n_clones", "sum"),
            n_detected=("n_detected", "sum"),
        )
        .sort_values("bin_min")
    )
    plot_data["detection_probability"] = plot_data["n_detected"] / plot_data["n_clones"]

    x_labels = [
        f"{row.bin_label}\n(n={int(row.n_clones)})"
        for row in plot_data.itertuples(index=False)
    ]
    y_values = plot_data["detection_probability"].tolist()
    x_positions = list(range(len(plot_data)))

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x_positions, y_values, marker="o")
    ax.set_xticks(x_positions, x_labels)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Source clone size bin")
    ax.set_ylabel("Detection probability")
    ax.set_title(DIRECTION_TITLES[direction])
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run_detection_curve_analysis(
    input_path: Path,
    output_dir: Path,
    cell_type: str | None = None,
    min_source_cells: int = 1,
    make_plots: bool = True,
    bin_visualizations: bool = False,
    bin_visualizations_dir: Path | None = None,
) -> None:
    """Run detection curve analysis and write CSV and PNG outputs."""
    df = pd.read_csv(input_path)
    if cell_type is not None:
        df = df.loc[df["cell_type"] == cell_type].copy()

    points = build_detection_points(df, min_source_cells=min_source_cells)
    summary = summarize_detection_curve(points)

    output_dir.mkdir(parents=True, exist_ok=True)
    points.to_csv(output_dir / "detection_curve_points.csv", index=False)
    summary.to_csv(output_dir / "detection_curve_summary.csv", index=False)

    if make_plots:
        plot_detection_curve(
            summary,
            direction="sf_to_blood",
            output_path=output_dir / DIRECTION_OUTPUT_FILES["sf_to_blood"],
        )
        plot_detection_curve(
            summary,
            direction="blood_to_sf",
            output_path=output_dir / DIRECTION_OUTPUT_FILES["blood_to_sf"],
        )

    if bin_visualizations:
        from tcr_bcr_tools.bin_visualizations import export_bin_visualizations

        bins_dir = bin_visualizations_dir or (output_dir / "bins")
        export_bin_visualizations(
            points,
            output_dir=bins_dir,
            cell_type=cell_type,
            global_summary_path=output_dir / "target_abundance_by_bin_summary.csv",
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build detection curve summaries and plots from paired detection table."
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
        help="Directory for detection curve outputs.",
    )
    parser.add_argument(
        "--cell-type",
        default=None,
        help="Keep only the specified cell type.",
    )
    parser.add_argument(
        "--min-source-cells",
        type=int,
        default=1,
        help="Minimum source clone size to include in the analysis.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Write CSV outputs only, without PNG plots.",
    )
    parser.add_argument(
        "--bin-visualizations",
        action="store_true",
        help="Export per-bin target abundance summaries and plots.",
    )
    parser.add_argument(
        "--bin-visualizations-dir",
        default=None,
        type=Path,
        help="Directory for bin-level visualizations (default: {output_dir}/bins).",
    )
    args = parser.parse_args()
    run_detection_curve_analysis(
        input_path=args.input,
        output_dir=args.output_dir,
        cell_type=args.cell_type,
        min_source_cells=args.min_source_cells,
        make_plots=not args.no_plots,
        bin_visualizations=args.bin_visualizations,
        bin_visualizations_dir=args.bin_visualizations_dir,
    )


if __name__ == "__main__":
    main()
