"""Correlation and regression between blood and SF clone fractions."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DEFAULT_PSEUDOCOUNT = 1e-6
OUTPUT_DIRNAME = "correlation_regression"

SCOPES = {"all_clones", "shared_clones", "blood_detected", "sf_detected"}
DEFAULT_SCOPES = sorted(SCOPES)

CORRELATION_SUMMARY_COLUMNS = [
    "scope",
    "cell_type",
    "n_clones",
    "pearson_fraction",
    "spearman_fraction",
    "kendall_fraction",
    "pearson_log_fraction",
    "spearman_log_fraction",
    "kendall_log_fraction",
]

REGRESSION_SUMMARY_COLUMNS = [
    "scope",
    "cell_type",
    "n_clones",
    "intercept",
    "slope",
    "r_squared",
    "rmse",
    "mae",
]

PREDICTION_COLUMNS = [
    "scope",
    "cell_type",
    "patient",
    "clonotype_key",
    "blood_fraction",
    "sf_fraction",
    "log_blood_fraction",
    "log_sf_fraction",
    "predicted_log_sf_fraction",
    "predicted_sf_fraction",
    "residual_log_sf_fraction",
]


def add_log_fractions(
    df: pd.DataFrame,
    pseudocount: float = DEFAULT_PSEUDOCOUNT,
) -> pd.DataFrame:
    """Add log10-transformed fraction columns with a pseudocount."""
    result = df.copy()
    result["log_blood_fraction"] = np.log10(result["blood_fraction"] + pseudocount)
    result["log_sf_fraction"] = np.log10(result["sf_fraction"] + pseudocount)
    return result


def filter_scope(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    """Filter clones according to the analysis scope."""
    if scope not in SCOPES:
        raise ValueError(
            f"Unsupported scope '{scope}'. "
            "Use one of: all_clones, shared_clones, blood_detected, sf_detected."
        )

    if scope == "all_clones":
        return df.copy()
    if scope == "shared_clones":
        return df.loc[df["shared_clone"] == True].copy()  # noqa: E712
    if scope == "blood_detected":
        return df.loc[df["blood_cells"] > 0].copy()
    return df.loc[df["sf_cells"] > 0].copy()


def _correlation_value(x: pd.Series, y: pd.Series, method: str) -> float:
    valid = x.notna() & y.notna()
    x_values = x.loc[valid].astype(float)
    y_values = y.loc[valid].astype(float)

    if len(x_values) < 3:
        return np.nan
    if x_values.nunique() <= 1 or y_values.nunique() <= 1:
        return np.nan
    return float(x_values.corr(y_values, method=method))


def _correlation_row(group: pd.DataFrame, scope: str, cell_type: str) -> dict:
    return {
        "scope": scope,
        "cell_type": cell_type,
        "n_clones": len(group),
        "pearson_fraction": _correlation_value(
            group["blood_fraction"], group["sf_fraction"], "pearson"
        ),
        "spearman_fraction": _correlation_value(
            group["blood_fraction"], group["sf_fraction"], "spearman"
        ),
        "kendall_fraction": _correlation_value(
            group["blood_fraction"], group["sf_fraction"], "kendall"
        ),
        "pearson_log_fraction": _correlation_value(
            group["log_blood_fraction"], group["log_sf_fraction"], "pearson"
        ),
        "spearman_log_fraction": _correlation_value(
            group["log_blood_fraction"], group["log_sf_fraction"], "spearman"
        ),
        "kendall_log_fraction": _correlation_value(
            group["log_blood_fraction"], group["log_sf_fraction"], "kendall"
        ),
    }


def compute_correlation_summary(
    df: pd.DataFrame,
    scopes: list[str] | None = None,
) -> pd.DataFrame:
    """Compute blood vs SF correlations for each scope and cell type."""
    selected_scopes = DEFAULT_SCOPES if scopes is None else scopes
    records: list[dict] = []

    for scope in selected_scopes:
        scoped_df = filter_scope(df, scope)
        for cell_type, group in scoped_df.groupby("cell_type", dropna=False):
            records.append(_correlation_row(group, scope, str(cell_type)))

    if not records:
        return pd.DataFrame(columns=CORRELATION_SUMMARY_COLUMNS)
    return pd.DataFrame(records)[CORRELATION_SUMMARY_COLUMNS]


def fit_linear_regression(df: pd.DataFrame) -> dict[str, float]:
    """Fit log_sf_fraction ~ log_blood_fraction using ordinary least squares."""
    x = df["log_blood_fraction"].astype(float)
    y = df["log_sf_fraction"].astype(float)
    valid = x.notna() & y.notna()
    x_values = x.loc[valid]
    y_values = y.loc[valid]

    nan_result = {
        "intercept": np.nan,
        "slope": np.nan,
        "r_squared": np.nan,
        "rmse": np.nan,
        "mae": np.nan,
    }

    if len(x_values) < 3:
        return nan_result
    if x_values.nunique() <= 1 or y_values.nunique() <= 1:
        return nan_result

    slope, intercept = np.polyfit(x_values, y_values, 1)
    predicted = intercept + slope * x_values
    residuals = y_values - predicted
    ss_res = float((residuals**2).sum())
    ss_tot = float(((y_values - y_values.mean()) ** 2).sum())
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

    return {
        "intercept": float(intercept),
        "slope": float(slope),
        "r_squared": float(r_squared),
        "rmse": float(np.sqrt((residuals**2).mean())),
        "mae": float(np.abs(residuals).mean()),
    }


def _regression_row(group: pd.DataFrame, scope: str, cell_type: str) -> dict:
    fit = fit_linear_regression(group)
    return {
        "scope": scope,
        "cell_type": cell_type,
        "n_clones": len(group),
        **fit,
    }


def _build_predictions(
    group: pd.DataFrame,
    cell_type: str,
    fit: dict[str, float],
    pseudocount: float,
) -> pd.DataFrame:
    predicted_log = fit["intercept"] + fit["slope"] * group["log_blood_fraction"]
    predicted_fraction = np.power(10.0, predicted_log) - pseudocount
    predicted_fraction = predicted_fraction.clip(lower=0.0)

    result = group[
        [
            "patient",
            "clonotype_key",
            "blood_fraction",
            "sf_fraction",
            "log_blood_fraction",
            "log_sf_fraction",
        ]
    ].copy()
    result.insert(0, "scope", "all_clones")
    result.insert(1, "cell_type", cell_type)
    result["predicted_log_sf_fraction"] = predicted_log
    result["predicted_sf_fraction"] = predicted_fraction
    result["residual_log_sf_fraction"] = (
        group["log_sf_fraction"] - predicted_log
    )
    return result[PREDICTION_COLUMNS]


def compute_regression_summary(
    df: pd.DataFrame,
    scopes: list[str] | None = None,
    pseudocount: float = DEFAULT_PSEUDOCOUNT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit regression models and build per-clone predictions for all_clones."""
    selected_scopes = DEFAULT_SCOPES if scopes is None else scopes
    summary_records: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []

    for scope in selected_scopes:
        scoped_df = filter_scope(df, scope)
        for cell_type, group in scoped_df.groupby("cell_type", dropna=False):
            cell_type_str = str(cell_type)
            fit = fit_linear_regression(group)
            summary_records.append(_regression_row(group, scope, cell_type_str))

            if scope == "all_clones":
                prediction_frames.append(
                    _build_predictions(group, cell_type_str, fit, pseudocount)
                )

    summary = (
        pd.DataFrame(columns=REGRESSION_SUMMARY_COLUMNS)
        if not summary_records
        else pd.DataFrame(summary_records)[REGRESSION_SUMMARY_COLUMNS]
    )
    predictions = (
        pd.DataFrame(columns=PREDICTION_COLUMNS)
        if not prediction_frames
        else pd.concat(prediction_frames, ignore_index=True)[PREDICTION_COLUMNS]
    )
    return summary, predictions


def plot_fraction_scatter(
    df: pd.DataFrame,
    output_path: Path,
    pseudocount: float = DEFAULT_PSEUDOCOUNT,
) -> None:
    """Plot blood vs SF clone fractions on log-log axes."""
    plot_df = df.copy()
    plot_df["plot_blood_fraction"] = plot_df["blood_fraction"].where(
        plot_df["blood_fraction"] > 0, pseudocount
    )
    plot_df["plot_sf_fraction"] = plot_df["sf_fraction"].where(
        plot_df["sf_fraction"] > 0, pseudocount
    )

    fig, ax = plt.subplots(figsize=(7, 6))
    if plot_df.empty:
        ax.set_title("Blood vs SF clone fractions")
    else:
        ax.scatter(
            plot_df["plot_blood_fraction"],
            plot_df["plot_sf_fraction"],
            alpha=0.4,
            s=10,
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("blood_fraction")
        ax.set_ylabel("sf_fraction")
        ax.set_title("Blood vs SF clone fractions")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_log_fraction_scatter(df: pd.DataFrame, output_path: Path) -> None:
    """Plot log-transformed blood vs SF clone fractions."""
    fig, ax = plt.subplots(figsize=(7, 6))
    if df.empty:
        ax.set_title("Log blood vs log SF clone fractions")
    else:
        ax.scatter(
            df["log_blood_fraction"],
            df["log_sf_fraction"],
            alpha=0.4,
            s=10,
        )
        ax.set_xlabel("log_blood_fraction")
        ax.set_ylabel("log_sf_fraction")
        ax.set_title("Log blood vs log SF clone fractions")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_regression_fit_by_cell_type(
    df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot log-log regression fits per cell type."""
    fig, ax = plt.subplots(figsize=(8, 6))
    cell_types = sorted(df["cell_type"].dropna().unique())

    if df.empty or not cell_types:
        ax.set_title("Regression fit by cell type")
    else:
        for cell_type in cell_types:
            cell_df = df.loc[df["cell_type"] == cell_type]
            ax.scatter(
                cell_df["log_blood_fraction"],
                cell_df["log_sf_fraction"],
                alpha=0.25,
                s=8,
                label=str(cell_type),
            )

            fit = fit_linear_regression(cell_df)
            if np.isnan(fit["slope"]):
                continue

            x_min = float(cell_df["log_blood_fraction"].min())
            x_max = float(cell_df["log_blood_fraction"].max())
            if x_min == x_max:
                continue

            x_line = np.linspace(x_min, x_max, 100)
            y_line = fit["intercept"] + fit["slope"] * x_line
            ax.plot(x_line, y_line, linewidth=2)

        ax.set_xlabel("log_blood_fraction")
        ax.set_ylabel("log_sf_fraction")
        ax.set_title("Regression fit by cell type")
        ax.legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_residuals_by_cell_type(
    predictions_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Plot boxplots of regression residuals by cell type."""
    plot_df = predictions_df.loc[predictions_df["scope"] == "all_clones"].copy()
    fig, ax = plt.subplots(figsize=(8, 5))

    if plot_df.empty:
        ax.set_title("Residuals by cell type")
    else:
        cell_types = sorted(plot_df["cell_type"].dropna().unique())
        data = [
            plot_df.loc[plot_df["cell_type"] == cell_type, "residual_log_sf_fraction"]
            for cell_type in cell_types
        ]
        ax.boxplot(data, tick_labels=cell_types)
        ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
        ax.set_xlabel("cell_type")
        ax.set_ylabel("residual_log_sf_fraction")
        ax.set_title("Residuals by cell type")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run_correlation_regression(
    input_path: Path,
    output_dir: Path,
    cell_type: str | None = None,
    scopes: list[str] | None = None,
    pseudocount: float = DEFAULT_PSEUDOCOUNT,
    make_plots: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run correlation and regression analysis and write outputs."""
    df = pd.read_csv(input_path)
    if cell_type is not None:
        df = df.loc[df["cell_type"] == cell_type].copy()

    df = add_log_fractions(df, pseudocount=pseudocount)
    correlation_summary = compute_correlation_summary(df, scopes=scopes)
    regression_summary, predictions = compute_regression_summary(
        df, scopes=scopes, pseudocount=pseudocount
    )

    out_dir = output_dir / OUTPUT_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    correlation_summary.to_csv(out_dir / "correlation_summary.csv", index=False)
    regression_summary.to_csv(out_dir / "regression_summary.csv", index=False)
    predictions.to_csv(out_dir / "regression_predictions.csv", index=False)

    if make_plots:
        plot_fraction_scatter(
            df, out_dir / "blood_vs_sf_fraction_scatter.png", pseudocount=pseudocount
        )
        plot_log_fraction_scatter(df, out_dir / "blood_vs_sf_log_fraction_scatter.png")
        plot_regression_fit_by_cell_type(
            df, predictions, out_dir / "regression_fit_by_cell_type.png"
        )
        plot_residuals_by_cell_type(predictions, out_dir / "residuals_by_cell_type.png")

    return correlation_summary, regression_summary, predictions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze correlation and regression between blood and SF clone fractions."
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
        "--scope",
        choices=sorted(SCOPES),
        default=None,
        help="Analyze a single scope. Default: all scopes.",
    )
    parser.add_argument(
        "--pseudocount",
        type=float,
        default=DEFAULT_PSEUDOCOUNT,
        help="Pseudocount added before log10 transformation.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Write CSV outputs only, without PNG plots.",
    )
    args = parser.parse_args()
    scopes = [args.scope] if args.scope is not None else None
    run_correlation_regression(
        input_path=args.input,
        output_dir=args.output_dir,
        cell_type=args.cell_type,
        scopes=scopes,
        pseudocount=args.pseudocount,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
