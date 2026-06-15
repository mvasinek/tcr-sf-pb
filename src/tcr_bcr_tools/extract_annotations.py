"""Combine per-sample contig annotation files into one table."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tcr_bcr_tools.io import find_annotation_files
from tcr_bcr_tools.metadata import parse_filename_metadata

ANNOTATION_COLUMNS = [
    "barcode",
    "is_cell",
    "contig_id",
    "high_confidence",
    "length",
    "chain",
    "v_gene",
    "d_gene",
    "j_gene",
    "c_gene",
    "full_length",
    "productive",
    "cdr3",
    "cdr3_nt",
    "reads",
    "umis",
    "raw_clonotype_id",
    "raw_consensus_id",
]

OUTPUT_COLUMNS = [
    "source_file",
    "gsm_id",
    "sample_group",
    "cell_type",
    "compartment",
    "patient",
    *ANNOTATION_COLUMNS,
]


def _apply_productive_filter(df: pd.DataFrame) -> pd.DataFrame:
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


def combine_annotation_files(
    input_dir: Path,
    output_path: Path,
    productive_only: bool = False,
) -> None:
    """Load annotation files from ``input_dir`` and write a combined CSV."""
    annotation_files = find_annotation_files(input_dir)
    if not annotation_files:
        raise FileNotFoundError(
            f"No files matching '*annotations.csv.gz' found in {input_dir}"
        )

    frames: list[pd.DataFrame] = []
    for file_path in annotation_files:
        metadata = parse_filename_metadata(file_path.name)
        df = pd.read_csv(file_path, compression="gzip")
        missing_columns = [col for col in ANNOTATION_COLUMNS if col not in df.columns]
        if missing_columns:
            raise ValueError(
                f"File {file_path} is missing required columns: {missing_columns}"
            )

        df = df[ANNOTATION_COLUMNS].assign(
            source_file=file_path.name,
            **metadata,
        )[OUTPUT_COLUMNS]

        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    if productive_only:
        combined = _apply_productive_filter(combined)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Combine TCR contig annotation files into one CSV table."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Directory containing annotation .csv.gz files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to the combined output CSV file.",
    )
    parser.add_argument(
        "--productive-only",
        action="store_true",
        help="Keep only productive, high-confidence TRA/TRB contigs with CDR3.",
    )
    args = parser.parse_args()
    combine_annotation_files(
        input_dir=args.input_dir,
        output_path=args.output,
        productive_only=args.productive_only,
    )


if __name__ == "__main__":
    main()
