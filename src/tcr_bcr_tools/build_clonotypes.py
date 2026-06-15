"""Build cell-level receptors and clone count tables from combined annotations."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

CELL_RECEPTOR_COLUMNS = [
    "source_file",
    "gsm_id",
    "sample_group",
    "patient",
    "compartment",
    "cell_type",
    "barcode",
    "tra_v_gene",
    "tra_j_gene",
    "tra_cdr3",
    "tra_umis",
    "trb_v_gene",
    "trb_j_gene",
    "trb_cdr3",
    "trb_umis",
    "has_tra",
    "has_trb",
    "is_paired",
    "clonotype_key",
]

CLONE_COUNT_COLUMNS = [
    "sample_group",
    "patient",
    "compartment",
    "cell_type",
    "clonotype_key",
    "n_cells",
    "n_paired_cells",
    "n_tra_only_cells",
    "n_trb_only_cells",
]

CELL_GROUP_COLUMNS = [
    "source_file",
    "gsm_id",
    "sample_group",
    "patient",
    "compartment",
    "cell_type",
    "barcode",
]


def filter_productive_tcr_contigs(df: pd.DataFrame) -> pd.DataFrame:
    """Keep productive, high-confidence TRA/TRB contigs with CDR3."""
    mask = (
        (df["is_cell"] == True)  # noqa: E712
        & (df["high_confidence"] == True)  # noqa: E712
        & (df["full_length"] == True)  # noqa: E712
        & (df["productive"] == True)  # noqa: E712
        & df["chain"].isin(["TRA", "TRB"])
        & df["cdr3"].notna()
        & (df["cdr3"] != "None")
    )
    return df.loc[mask].copy()


def select_dominant_chain(df: pd.DataFrame, chain: str) -> pd.DataFrame:
    """Select one dominant contig per cell for the given chain."""
    chain_df = df.loc[df["chain"] == chain].copy()
    if chain_df.empty:
        return chain_df

    chain_df = chain_df.sort_values(
        ["umis", "reads", "cdr3"],
        ascending=[False, False, True],
    )
    return chain_df.drop_duplicates(subset=["source_file", "barcode"], keep="first")


def build_clonotype_key(row: pd.Series) -> str:
    """Build a deterministic clonotype key from dominant TRA/TRB chains."""
    if row["has_tra"] and row["has_trb"]:
        return (
            f"TRA:{row['tra_v_gene']}|{row['tra_j_gene']}|{row['tra_cdr3']}"
            f"__TRB:{row['trb_v_gene']}|{row['trb_j_gene']}|{row['trb_cdr3']}"
        )
    if row["has_tra"]:
        return (
            f"TRA:{row['tra_v_gene']}|{row['tra_j_gene']}|{row['tra_cdr3']}"
            "__TRB:missing"
        )
    if row["has_trb"]:
        return (
            "TRA:missing__"
            f"TRB:{row['trb_v_gene']}|{row['trb_j_gene']}|{row['trb_cdr3']}"
        )
    return "TRA:missing__TRB:missing"


def build_cell_receptors(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse contig-level annotations to one receptor row per cell."""
    filtered = filter_productive_tcr_contigs(df)
    cells = filtered[CELL_GROUP_COLUMNS].drop_duplicates()

    tra = select_dominant_chain(filtered, "TRA")
    if not tra.empty:
        tra_data = tra[["source_file", "barcode", "v_gene", "j_gene", "cdr3", "umis"]].rename(
            columns={
                "v_gene": "tra_v_gene",
                "j_gene": "tra_j_gene",
                "cdr3": "tra_cdr3",
                "umis": "tra_umis",
            }
        )
        cells = cells.merge(tra_data, on=["source_file", "barcode"], how="left")
    else:
        cells = cells.assign(
            tra_v_gene=pd.NA,
            tra_j_gene=pd.NA,
            tra_cdr3=pd.NA,
            tra_umis=pd.NA,
        )

    trb = select_dominant_chain(filtered, "TRB")
    if not trb.empty:
        trb_data = trb[["source_file", "barcode", "v_gene", "j_gene", "cdr3", "umis"]].rename(
            columns={
                "v_gene": "trb_v_gene",
                "j_gene": "trb_j_gene",
                "cdr3": "trb_cdr3",
                "umis": "trb_umis",
            }
        )
        cells = cells.merge(trb_data, on=["source_file", "barcode"], how="left")
    else:
        cells = cells.assign(
            trb_v_gene=pd.NA,
            trb_j_gene=pd.NA,
            trb_cdr3=pd.NA,
            trb_umis=pd.NA,
        )

    cells["has_tra"] = cells["tra_cdr3"].notna()
    cells["has_trb"] = cells["trb_cdr3"].notna()
    cells["is_paired"] = cells["has_tra"] & cells["has_trb"]
    cells["clonotype_key"] = cells.apply(build_clonotype_key, axis=1)

    return cells[CELL_RECEPTOR_COLUMNS].copy()


def build_clone_counts(
    cell_df: pd.DataFrame, paired_only: bool = False
) -> pd.DataFrame:
    """Aggregate cell receptors into per-sample clone count rows."""
    df = cell_df.copy()
    if paired_only:
        df = df.loc[df["is_paired"] == True].copy()  # noqa: E712

    df["is_tra_only"] = df["has_tra"] & ~df["has_trb"]
    df["is_trb_only"] = ~df["has_tra"] & df["has_trb"]

    group_columns = [
        "sample_group",
        "patient",
        "compartment",
        "cell_type",
        "clonotype_key",
    ]
    counts = (
        df.groupby(group_columns, as_index=False)
        .agg(
            n_cells=("barcode", "count"),
            n_paired_cells=("is_paired", "sum"),
            n_tra_only_cells=("is_tra_only", "sum"),
            n_trb_only_cells=("is_trb_only", "sum"),
        )
        .astype(
            {
                "n_cells": int,
                "n_paired_cells": int,
                "n_tra_only_cells": int,
                "n_trb_only_cells": int,
            }
        )
    )
    return counts[CLONE_COUNT_COLUMNS]


def build_clonotype_tables(
    input_path: Path,
    cell_output: Path,
    clone_output: Path,
    paired_only: bool = False,
) -> None:
    """Load combined annotations and write cell receptor and clone count tables."""
    df = pd.read_csv(input_path)
    cell_receptors = build_cell_receptors(df)
    clone_counts = build_clone_counts(cell_receptors, paired_only=paired_only)

    cell_output.parent.mkdir(parents=True, exist_ok=True)
    clone_output.parent.mkdir(parents=True, exist_ok=True)
    cell_receptors.to_csv(cell_output, index=False)
    clone_counts.to_csv(clone_output, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build cell receptor and clone count tables from combined annotations."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to combined_annotations.csv.",
    )
    parser.add_argument(
        "--cell-output",
        required=True,
        type=Path,
        help="Path to the cell_receptors.csv output file.",
    )
    parser.add_argument(
        "--clone-output",
        required=True,
        type=Path,
        help="Path to the clone_counts.csv output file.",
    )
    parser.add_argument(
        "--paired-only",
        action="store_true",
        help="Count clones using only paired TRA/TRB cells.",
    )
    args = parser.parse_args()
    build_clonotype_tables(
        input_path=args.input,
        cell_output=args.cell_output,
        clone_output=args.clone_output,
        paired_only=args.paired_only,
    )


if __name__ == "__main__":
    main()
