"""Sweep expansion concordance metrics across multiple thresholds."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tcr_bcr_tools.expansion_concordance import (
    CONCORDANCE_SUMMARY_COLUMNS,
    classify_expansion,
    summarize_expansion_concordance,
)

DEFAULT_THRESHOLDS: dict[str, list[float]] = {
    "fraction": [0.0005, 0.001, 0.002, 0.003, 0.005, 0.0075, 0.01, 0.02, 0.05],
    "cells": [2, 3, 5, 10, 20, 50, 100],
    "quantile": [0.80, 0.85, 0.90, 0.95, 0.975, 0.99],
}

SWEEP_PATIENT_COLUMNS = [
    "patient",
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

SWEEP_OUTPUT_DIRNAME = "threshold_sweep"


def get_default_thresholds(method: str) -> list[float]:
    """Return default threshold grid for an expansion method."""
    if method not in DEFAULT_THRESHOLDS:
        raise ValueError(
            f"Unsupported expansion method '{method}'. "
            "Use one of: fraction, cells, quantile."
        )
    return DEFAULT_THRESHOLDS[method].copy()


def parse_thresholds(value: str | None, method: str) -> list[float]:
    """Parse a comma-separated threshold list or return method defaults."""
    if value is None:
        return get_default_thresholds(method)
    thresholds = [float(item.strip()) for item in value.split(",") if item.strip()]
    if not thresholds:
        raise ValueError("At least one threshold must be provided.")
    return thresholds


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


def _summarize_patient_sweep(
    status_df: pd.DataFrame, method: str, threshold: float
) -> pd.DataFrame:
    records: list[dict] = []
    for (patient, cell_type), group in status_df.groupby(
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
    if not records:
        return pd.DataFrame(columns=SWEEP_PATIENT_COLUMNS)
    return pd.DataFrame(records)[SWEEP_PATIENT_COLUMNS]


def run_threshold_sweep(
    df: pd.DataFrame,
    method: str = "fraction",
    thresholds: list[float] | None = None,
    cell_type: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run expansion concordance analysis across multiple thresholds."""
    if method not in DEFAULT_THRESHOLDS:
        raise ValueError(
            f"Unsupported expansion method '{method}'. "
            "Use one of: fraction, cells, quantile."
        )

    filtered = df.copy()
    if cell_type is not None:
        filtered = filtered.loc[filtered["cell_type"] == cell_type].copy()

    threshold_values = thresholds or get_default_thresholds(method)
    summary_parts: list[pd.DataFrame] = []
    patient_parts: list[pd.DataFrame] = []

    for threshold in threshold_values:
        status = classify_expansion(filtered, method=method, threshold=threshold)
        summary_parts.append(
            summarize_expansion_concordance(status, method=method, threshold=threshold)
        )
        patient_parts.append(_summarize_patient_sweep(status, method, threshold))

    summary = (
        pd.concat(summary_parts, ignore_index=True)
        if summary_parts
        else pd.DataFrame(columns=CONCORDANCE_SUMMARY_COLUMNS)
    )
    patient_summary = (
        pd.concat(patient_parts, ignore_index=True)
        if patient_parts
        else pd.DataFrame(columns=SWEEP_PATIENT_COLUMNS)
    )
    return summary, patient_summary


def plot_threshold_sweep_curves(
    summary_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot conditional expansion probabilities across thresholds."""
    fig, ax = plt.subplots(figsize=(9, 5))
    if summary_df.empty:
        ax.set_title("Expansion concordance vs threshold")
        ax.set_ylim(0, 1)
    else:
        method = summary_df["expansion_method"].iloc[0]
        use_log_x = method == "cells"
        for cell_type, group in summary_df.groupby("cell_type", dropna=False):
            ordered = group.sort_values("expansion_threshold")
            x_values = ordered["expansion_threshold"].tolist()
            ax.plot(
                x_values,
                ordered["p_sf_expanded_given_blood_expanded"],
                marker="o",
                label=f"{cell_type}: P(SF|blood)",
            )
            ax.plot(
                x_values,
                ordered["p_blood_expanded_given_sf_expanded"],
                marker="s",
                linestyle="--",
                label=f"{cell_type}: P(blood|SF)",
            )
        if use_log_x:
            ax.set_xscale("log")
        ax.set_ylim(0, 1)
        ax.set_xlabel("expansion_threshold")
        ax.set_ylabel("Conditional probability")
        ax.set_title(f"Expansion concordance vs threshold ({method})")
        ax.legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_threshold_sweep_jaccard(
    summary_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot Jaccard index of expanded clones across thresholds."""
    fig, ax = plt.subplots(figsize=(8, 5))
    if summary_df.empty:
        ax.set_title("Jaccard index vs threshold")
        ax.set_ylim(0, 1)
    else:
        method = summary_df["expansion_method"].iloc[0]
        use_log_x = method == "cells"
        for cell_type, group in summary_df.groupby("cell_type", dropna=False):
            ordered = group.sort_values("expansion_threshold")
            ax.plot(
                ordered["expansion_threshold"],
                ordered["jaccard_expanded"],
                marker="o",
                label=str(cell_type),
            )
        if use_log_x:
            ax.set_xscale("log")
        ax.set_ylim(0, 1)
        ax.set_xlabel("expansion_threshold")
        ax.set_ylabel("Jaccard index of expanded clones")
        ax.set_title(f"Jaccard index vs threshold ({method})")
        ax.legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_expanded_counts_by_threshold(
    summary_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot expanded clone counts across thresholds."""
    fig, ax = plt.subplots(figsize=(9, 5))
    if summary_df.empty:
        ax.set_title("Expanded clone counts vs threshold")
    else:
        method = summary_df["expansion_method"].iloc[0]
        use_log_x = method == "cells"
        for cell_type, group in summary_df.groupby("cell_type", dropna=False):
            ordered = group.sort_values("expansion_threshold")
            x_values = ordered["expansion_threshold"].tolist()
            ax.plot(
                x_values,
                ordered["n_sf_expanded"],
                marker="o",
                label=f"{cell_type}: n_sf_expanded",
            )
            ax.plot(
                x_values,
                ordered["n_blood_expanded"],
                marker="s",
                linestyle="--",
                label=f"{cell_type}: n_blood_expanded",
            )
            ax.plot(
                x_values,
                ordered["n_expanded_both"],
                marker="^",
                linestyle=":",
                label=f"{cell_type}: n_expanded_both",
            )
        if use_log_x:
            ax.set_xscale("log")
        ax.set_xlabel("expansion_threshold")
        ax.set_ylabel("Number of expanded clones")
        ax.set_title(f"Expanded clone counts vs threshold ({method})")
        ax.legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run_threshold_sweep_cli(
    input_path: Path,
    output_dir: Path,
    method: str = "fraction",
    thresholds: list[float] | None = None,
    cell_type: str | None = None,
    make_plots: bool = True,
) -> None:
    """Load data, run threshold sweep, and write outputs."""
    df = pd.read_csv(input_path)
    summary, patient_summary = run_threshold_sweep(
        df,
        method=method,
        thresholds=thresholds,
        cell_type=cell_type,
    )

    sweep_dir = output_dir / SWEEP_OUTPUT_DIRNAME
    sweep_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(sweep_dir / "threshold_sweep_summary.csv", index=False)
    patient_summary.to_csv(sweep_dir / "threshold_sweep_by_patient.csv", index=False)

    if make_plots:
        plot_threshold_sweep_curves(summary, sweep_dir / "threshold_sweep_curves.png")
        plot_threshold_sweep_jaccard(summary, sweep_dir / "threshold_sweep_jaccard.png")
        plot_expanded_counts_by_threshold(
            summary, sweep_dir / "threshold_sweep_expanded_counts.png"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sweep expansion concordance metrics across thresholds."
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
        help="Base output directory (sweep files go to {output_dir}/threshold_sweep/).",
    )
    parser.add_argument(
        "--method",
        choices=["fraction", "cells", "quantile"],
        default="fraction",
        help="Expansion definition method to sweep.",
    )
    parser.add_argument(
        "--thresholds",
        default=None,
        help="Comma-separated thresholds (defaults depend on --method).",
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
    run_threshold_sweep_cli(
        input_path=args.input,
        output_dir=args.output_dir,
        method=args.method,
        thresholds=parse_thresholds(args.thresholds, args.method),
        cell_type=args.cell_type,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
