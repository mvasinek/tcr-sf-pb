"""Expansion concordance analysis between SF and blood compartments."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

EXPANSION_STATUS_TABLE_COLUMNS = [
    "patient",
    "cell_type",
    "clonotype_key",
    "sf_cells",
    "blood_cells",
    "sf_fraction",
    "blood_fraction",
    "sf_expanded",
    "blood_expanded",
    "expansion_status",
    "detected_in_sf",
    "detected_in_blood",
    "shared_clone",
]

CONCORDANCE_SUMMARY_COLUMNS = [
    "cell_type",
    "expansion_method",
    "expansion_threshold",
    "n_clones",
    "n_sf_expanded",
    "n_blood_expanded",
    "n_expanded_both",
    "n_expanded_sf_only",
    "n_expanded_blood_only",
    "p_sf_expanded_given_blood_expanded",
    "p_blood_expanded_given_sf_expanded",
    "jaccard_expanded",
]

PATIENT_CONCORDANCE_COLUMNS = [
    "patient",
    "cell_type",
    "expansion_method",
    "expansion_threshold",
    "n_clones",
    "n_sf_expanded",
    "n_blood_expanded",
    "n_expanded_both",
    "p_sf_expanded_given_blood_expanded",
    "p_blood_expanded_given_sf_expanded",
    "jaccard_expanded",
]

EXPANSION_STATUS_ORDER = [
    "expanded_both",
    "expanded_sf_only",
    "expanded_blood_only",
    "not_expanded",
]

FRACTION_PSEUDOCOUNT = 1e-6


def _assign_expansion_status(
    sf_expanded: pd.Series, blood_expanded: pd.Series
) -> pd.Series:
    status = pd.Series("not_expanded", index=sf_expanded.index, dtype=str)
    status.loc[sf_expanded & blood_expanded] = "expanded_both"
    status.loc[sf_expanded & ~blood_expanded] = "expanded_sf_only"
    status.loc[~sf_expanded & blood_expanded] = "expanded_blood_only"
    return status


def _quantile_expansion_flags(
    df: pd.DataFrame, fraction_column: str, presence_column: str, threshold: float
) -> pd.Series:
    expanded = pd.Series(False, index=df.index)
    group_columns = ["patient", "cell_type"]

    for _, group in df.groupby(group_columns, dropna=False):
        present = group.loc[group[presence_column] == True]  # noqa: E712
        if present.empty:
            continue
        cutoff = present[fraction_column].quantile(threshold)
        expanded.loc[present.index] = present[fraction_column] >= cutoff

    return expanded


def classify_expansion(
    df: pd.DataFrame,
    method: str = "fraction",
    threshold: float = 0.005,
) -> pd.DataFrame:
    """Classify SF and blood expansion status for each clone."""
    if method not in {"fraction", "cells", "quantile"}:
        raise ValueError(
            f"Unsupported expansion method '{method}'. "
            "Use one of: fraction, cells, quantile."
        )

    result = df.copy()
    if method == "fraction":
        result["sf_expanded"] = result["sf_fraction"] >= threshold
        result["blood_expanded"] = result["blood_fraction"] >= threshold
    elif method == "cells":
        result["sf_expanded"] = result["sf_cells"] >= threshold
        result["blood_expanded"] = result["blood_cells"] >= threshold
    else:
        result["sf_expanded"] = _quantile_expansion_flags(
            result,
            fraction_column="sf_fraction",
            presence_column="detected_in_sf",
            threshold=threshold,
        )
        result["blood_expanded"] = _quantile_expansion_flags(
            result,
            fraction_column="blood_fraction",
            presence_column="detected_in_blood",
            threshold=threshold,
        )

    result["expansion_status"] = _assign_expansion_status(
        result["sf_expanded"], result["blood_expanded"]
    )
    return result[EXPANSION_STATUS_TABLE_COLUMNS].copy()


def _concordance_metrics(group: pd.DataFrame) -> dict[str, float | int]:
    n_clones = len(group)
    n_sf_expanded = int(group["sf_expanded"].sum())
    n_blood_expanded = int(group["blood_expanded"].sum())
    n_expanded_both = int((group["sf_expanded"] & group["blood_expanded"]).sum())
    n_expanded_sf_only = int(
        (group["sf_expanded"] & ~group["blood_expanded"]).sum()
    )
    n_expanded_blood_only = int(
        (~group["sf_expanded"] & group["blood_expanded"]).sum()
    )

    p_sf_given_blood = (
        n_expanded_both / n_blood_expanded if n_blood_expanded > 0 else np.nan
    )
    p_blood_given_sf = (
        n_expanded_both / n_sf_expanded if n_sf_expanded > 0 else np.nan
    )
    union = n_sf_expanded + n_blood_expanded - n_expanded_both
    jaccard = n_expanded_both / union if union > 0 else np.nan

    return {
        "n_clones": n_clones,
        "n_sf_expanded": n_sf_expanded,
        "n_blood_expanded": n_blood_expanded,
        "n_expanded_both": n_expanded_both,
        "n_expanded_sf_only": n_expanded_sf_only,
        "n_expanded_blood_only": n_expanded_blood_only,
        "p_sf_expanded_given_blood_expanded": p_sf_given_blood,
        "p_blood_expanded_given_sf_expanded": p_blood_given_sf,
        "jaccard_expanded": jaccard,
    }


def summarize_expansion_concordance(
    df: pd.DataFrame,
    method: str,
    threshold: float,
) -> pd.DataFrame:
    """Summarize expansion concordance by cell type."""
    if df.empty:
        return pd.DataFrame(columns=CONCORDANCE_SUMMARY_COLUMNS)

    records: list[dict] = []
    for cell_type, group in df.groupby("cell_type", dropna=False):
        record = {
            "cell_type": cell_type,
            "expansion_method": method,
            "expansion_threshold": threshold,
        }
        record.update(_concordance_metrics(group))
        records.append(record)

    return pd.DataFrame(records)[CONCORDANCE_SUMMARY_COLUMNS]


def summarize_expansion_concordance_by_patient(
    df: pd.DataFrame,
    method: str,
    threshold: float,
) -> pd.DataFrame:
    """Summarize expansion concordance by patient and cell type."""
    if df.empty:
        return pd.DataFrame(columns=PATIENT_CONCORDANCE_COLUMNS)

    records: list[dict] = []
    for (patient, cell_type), group in df.groupby(
        ["patient", "cell_type"], dropna=False
    ):
        record = {
            "patient": patient,
            "cell_type": cell_type,
            "expansion_method": method,
            "expansion_threshold": threshold,
        }
        record.update(_concordance_metrics(group))
        records.append(record)

    return pd.DataFrame(records)[PATIENT_CONCORDANCE_COLUMNS]


def plot_expansion_status_counts(df: pd.DataFrame, output_path: Path) -> None:
    """Plot counts of expansion status categories."""
    counts = (
        df["expansion_status"]
        .value_counts()
        .reindex(EXPANSION_STATUS_ORDER, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(counts.index, counts.values)
    ax.set_xlabel("expansion_status")
    ax.set_ylabel("Number of clones")
    ax.set_title("Expansion status counts")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_sf_vs_blood_fraction_scatter(df: pd.DataFrame, output_path: Path) -> None:
    """Plot SF vs blood clone fractions on a log-log scatter."""
    plot_df = df.copy()
    plot_df["plot_sf_fraction"] = plot_df["sf_fraction"].where(
        plot_df["sf_fraction"] > 0, FRACTION_PSEUDOCOUNT
    )
    plot_df["plot_blood_fraction"] = plot_df["blood_fraction"].where(
        plot_df["blood_fraction"] > 0, FRACTION_PSEUDOCOUNT
    )

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(
        plot_df["plot_blood_fraction"],
        plot_df["plot_sf_fraction"],
        alpha=0.5,
        s=12,
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("blood_fraction")
    ax.set_ylabel("sf_fraction")
    ax.set_title("SF vs blood clone fractions")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_patient_concordance_matrix(summary_df: pd.DataFrame, output_path: Path) -> None:
    """Plot patient-level P(SF expanded | blood expanded) as a matrix."""
    if summary_df.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No patient concordance data", ha="center", va="center")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    matrix = summary_df.pivot_table(
        index="patient",
        columns="cell_type",
        values="p_sf_expanded_given_blood_expanded",
        aggfunc="first",
    )
    matrix = matrix.sort_index()

    fig, ax = plt.subplots(
        figsize=(max(6, matrix.shape[1] * 1.5), max(4, matrix.shape[0] * 0.5))
    )
    image = ax.imshow(matrix.values.astype(float), aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(matrix.shape[1]), matrix.columns.tolist())
    ax.set_yticks(range(matrix.shape[0]), matrix.index.tolist())
    ax.set_xlabel("cell_type")
    ax.set_ylabel("patient")
    ax.set_title("P(SF expanded | blood expanded)")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run_expansion_concordance_analysis(
    input_path: Path,
    output_dir: Path,
    method: str = "fraction",
    threshold: float = 0.005,
    cell_type: str | None = None,
    make_plots: bool = True,
) -> None:
    """Run expansion concordance analysis and write outputs."""
    df = pd.read_csv(input_path)
    if cell_type is not None:
        df = df.loc[df["cell_type"] == cell_type].copy()

    status_table = classify_expansion(df, method=method, threshold=threshold)
    summary = summarize_expansion_concordance(status_table, method, threshold)
    patient_summary = summarize_expansion_concordance_by_patient(
        status_table, method, threshold
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    status_table.to_csv(output_dir / "expansion_status_table.csv", index=False)
    summary.to_csv(output_dir / "expansion_concordance_summary.csv", index=False)
    patient_summary.to_csv(
        output_dir / "expansion_concordance_by_patient.csv", index=False
    )

    if make_plots:
        expansion_dir = output_dir / "expansion"
        plot_expansion_status_counts(
            status_table, expansion_dir / "expansion_status_counts.png"
        )
        plot_sf_vs_blood_fraction_scatter(
            status_table, expansion_dir / "sf_vs_blood_fraction_scatter.png"
        )
        plot_patient_concordance_matrix(
            patient_summary, expansion_dir / "patient_concordance_matrix.png"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze expansion concordance between SF and blood compartments."
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
        help="Directory for expansion concordance outputs.",
    )
    parser.add_argument(
        "--expansion-method",
        choices=["fraction", "cells", "quantile"],
        default="fraction",
        help="Method used to define expanded clones.",
    )
    parser.add_argument(
        "--expansion-threshold",
        type=float,
        default=0.005,
        help="Expansion threshold (fraction, cell count, or quantile).",
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
    run_expansion_concordance_analysis(
        input_path=args.input,
        output_dir=args.output_dir,
        method=args.expansion_method,
        threshold=args.expansion_threshold,
        cell_type=args.cell_type,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
