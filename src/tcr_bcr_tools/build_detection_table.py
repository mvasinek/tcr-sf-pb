"""Build paired SF/blood clone detection tables from clone counts."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DETECTION_TABLE_COLUMNS = [
    "patient",
    "cell_type",
    "clonotype_key",
    "sf_sample_group",
    "blood_sample_group",
    "sf_cells",
    "blood_cells",
    "sf_paired_cells",
    "blood_paired_cells",
    "sf_tra_only_cells",
    "blood_tra_only_cells",
    "sf_trb_only_cells",
    "blood_trb_only_cells",
    "detected_in_sf",
    "detected_in_blood",
    "shared_clone",
    "sf_fraction",
    "blood_fraction",
]

PAIRING_KEYS = ["patient", "cell_type", "clonotype_key"]

COUNT_COLUMNS = [
    "n_cells",
    "n_paired_cells",
    "n_tra_only_cells",
    "n_trb_only_cells",
]

SF_COLUMN_MAP = {
    "n_cells": "sf_cells",
    "n_paired_cells": "sf_paired_cells",
    "n_tra_only_cells": "sf_tra_only_cells",
    "n_trb_only_cells": "sf_trb_only_cells",
    "sample_groups": "sf_sample_group",
}

BLOOD_COLUMN_MAP = {
    "n_cells": "blood_cells",
    "n_paired_cells": "blood_paired_cells",
    "n_tra_only_cells": "blood_tra_only_cells",
    "n_trb_only_cells": "blood_trb_only_cells",
    "sample_groups": "blood_sample_group",
}

COMPARTMENT_ALIASES = {
    "sf": "SF",
    "synovialfluid": "SF",
    "synovial_fluid": "SF",
    "blood": "blood",
    "pb": "blood",
    "peripheral_blood": "blood",
}


def normalize_compartment(value: str) -> str | None:
    """Map compartment aliases to supported values ``SF`` or ``blood``."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    text = str(value).strip()
    if text == "SF":
        return "SF"

    key = text.lower().replace(" ", "_")
    return COMPARTMENT_ALIASES.get(key)


def _join_sample_groups(groups: pd.Series) -> str:
    """Join unique sample groups in deterministic alphabetical order."""
    return ";".join(sorted(groups.astype(str).unique()))


def _normalize_compartments(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize compartment values and drop unsupported rows with warnings."""
    original = df["compartment"].copy()
    normalized = original.map(normalize_compartment)
    unsupported = original.loc[normalized.isna()].dropna().unique()
    for value in unsupported:
        print(f"Warning: ignoring unsupported compartment '{value}'")

    result = df.copy()
    result["compartment"] = normalized
    return result.loc[result["compartment"].notna()].copy()


def filter_clone_counts(
    df: pd.DataFrame,
    cell_type: str | None = None,
    sample_group: str | None = None,
    min_cells: int = 1,
) -> pd.DataFrame:
    """Filter clone count rows before building the detection table."""
    result = df.copy()
    if cell_type is not None:
        result = result.loc[result["cell_type"] == cell_type]
    if sample_group is not None:
        result = result.loc[result["sample_group"] == sample_group]
    if min_cells > 1:
        clone_max = (
            result.groupby(PAIRING_KEYS, as_index=False)["n_cells"]
            .max()
            .rename(columns={"n_cells": "max_compartment_cells"})
        )
        valid_clones = clone_max.loc[
            clone_max["max_compartment_cells"] >= min_cells, PAIRING_KEYS
        ]
        result = result.merge(valid_clones, on=PAIRING_KEYS, how="inner")
    return result


def calculate_compartment_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Sum cell counts per patient, cell type, and compartment."""
    return (
        df.groupby(["patient", "cell_type", "compartment"], as_index=False)
        .agg(total_cells=("n_cells", "sum"))
    )


EMPTY_COMPARTMENT_COLUMNS = PAIRING_KEYS + COUNT_COLUMNS + ["sample_groups"]


def _aggregate_compartment(df: pd.DataFrame, compartment: str) -> pd.DataFrame:
    """Aggregate clone counts and sample groups for one compartment."""
    subset = df.loc[df["compartment"] == compartment]
    if subset.empty:
        return pd.DataFrame(columns=EMPTY_COMPARTMENT_COLUMNS)

    return subset.groupby(PAIRING_KEYS, as_index=False).agg(
        n_cells=("n_cells", "sum"),
        n_paired_cells=("n_paired_cells", "sum"),
        n_tra_only_cells=("n_tra_only_cells", "sum"),
        n_trb_only_cells=("n_trb_only_cells", "sum"),
        sample_groups=("sample_group", _join_sample_groups),
    )


def build_paired_detection_table(
    df: pd.DataFrame, min_cells: int = 1
) -> pd.DataFrame:
    """Pivot SF and blood clone counts into one row per patient clone."""
    if df.empty:
        return pd.DataFrame(columns=DETECTION_TABLE_COLUMNS)

    totals = calculate_compartment_totals(df)

    sf = _aggregate_compartment(df, "SF").rename(columns=SF_COLUMN_MAP)
    blood = _aggregate_compartment(df, "blood").rename(columns=BLOOD_COLUMN_MAP)

    result = sf.merge(blood, on=PAIRING_KEYS, how="outer")

    value_columns = [
        "sf_cells",
        "blood_cells",
        "sf_paired_cells",
        "blood_paired_cells",
        "sf_tra_only_cells",
        "blood_tra_only_cells",
        "sf_trb_only_cells",
        "blood_trb_only_cells",
    ]
    result[value_columns] = result[value_columns].fillna(0).astype(int)
    result["sf_sample_group"] = result["sf_sample_group"].fillna("")
    result["blood_sample_group"] = result["blood_sample_group"].fillna("")

    result["detected_in_sf"] = result["sf_cells"] > 0
    result["detected_in_blood"] = result["blood_cells"] > 0
    result["shared_clone"] = result["detected_in_sf"] & result["detected_in_blood"]

    sf_totals = totals.loc[totals["compartment"] == "SF"].rename(
        columns={"total_cells": "sf_total"}
    )
    blood_totals = totals.loc[totals["compartment"] == "blood"].rename(
        columns={"total_cells": "blood_total"}
    )

    result = result.merge(
        sf_totals[["patient", "cell_type", "sf_total"]],
        on=["patient", "cell_type"],
        how="left",
    )
    result = result.merge(
        blood_totals[["patient", "cell_type", "blood_total"]],
        on=["patient", "cell_type"],
        how="left",
    )

    result["sf_fraction"] = result["sf_cells"] / result["sf_total"].fillna(0)
    result["blood_fraction"] = result["blood_cells"] / result["blood_total"].fillna(0)
    result.loc[result["sf_total"].fillna(0) == 0, "sf_fraction"] = 0.0
    result.loc[result["blood_total"].fillna(0) == 0, "blood_fraction"] = 0.0

    result = result.loc[result[["sf_cells", "blood_cells"]].max(axis=1) >= min_cells]

    return result[DETECTION_TABLE_COLUMNS].copy()


def write_detection_table(df: pd.DataFrame, output_path: Path) -> None:
    """Write the paired detection table to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def build_detection_table(
    input_path: Path,
    output_path: Path,
    cell_type: str | None = None,
    sample_group: str | None = None,
    min_cells: int = 1,
) -> None:
    """Load clone counts and write the paired detection table."""
    df = pd.read_csv(input_path)
    df = _normalize_compartments(df)
    df = filter_clone_counts(
        df,
        cell_type=cell_type,
        sample_group=sample_group,
        min_cells=min_cells,
    )
    table = build_paired_detection_table(df, min_cells=min_cells)
    write_detection_table(table, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build paired SF/blood clone detection table from clone counts."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to clone_counts.csv.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to paired_detection_table.csv.",
    )
    parser.add_argument(
        "--cell-type",
        default=None,
        help="Keep only the specified cell type.",
    )
    parser.add_argument(
        "--sample-group",
        default=None,
        help="Keep only the specified sample group.",
    )
    parser.add_argument(
        "--min-cells",
        type=int,
        default=1,
        help="Minimum clone size in at least one compartment.",
    )
    args = parser.parse_args()
    build_detection_table(
        input_path=args.input,
        output_path=args.output,
        cell_type=args.cell_type,
        sample_group=args.sample_group,
        min_cells=args.min_cells,
    )


if __name__ == "__main__":
    main()
