"""10x Genomics contig annotation adapter."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tcr_bcr_tools.adapters.base import AdapterValidationResult, BaseAdapter
from tcr_bcr_tools.adapters.schema import REQUIRED_COLUMNS
from tcr_bcr_tools.adapters.validation import validate_unified_schema
from tcr_bcr_tools.metadata import parse_filename_metadata
from tcr_bcr_tools.project.manifest import load_yaml

TENX_ANNOTATION_COLUMNS = [
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


def find_tenx_annotation_files(input_dir: Path) -> list[Path]:
    """Find 10x annotation files in a dataset raw directory."""
    patterns = ("*annotations.csv.gz", "*filtered_contig_annotations.csv.gz")
    found: list[Path] = []
    for pattern in patterns:
        found.extend(sorted(input_dir.rglob(pattern)))
    unique = sorted({path.resolve() for path in found})
    return unique


def _raw_input_dir(dataset_path: Path) -> Path:
    manifest_path = dataset_path / "dataset.yaml"
    if manifest_path.exists():
        data = load_yaml(manifest_path)
        raw_source = data.get("files", {}).get("raw_source")
        if raw_source:
            source = Path(raw_source)
            if source.exists():
                return source
    raw_dir = dataset_path / "raw"
    return raw_dir


def _dataset_id(dataset_path: Path, dataset_id: str) -> str:
    if dataset_id:
        return dataset_id
    manifest_path = dataset_path / "dataset.yaml"
    if manifest_path.exists():
        data = load_yaml(manifest_path)
        return str(data.get("dataset", {}).get("id", dataset_path.name))
    return dataset_path.name


class TenXAdapter(BaseAdapter):
    """Normalize 10x filtered contig annotations to unified schema."""

    name = "tenx"
    version = "0.5.3"
    description = "10x Genomics filtered contig annotations adapter."

    @classmethod
    def validate_input(cls, dataset_path: Path) -> AdapterValidationResult:
        raw_dir = _raw_input_dir(dataset_path)
        errors: list[str] = []
        warnings: list[str] = []
        detected = find_tenx_annotation_files(raw_dir) if raw_dir.is_dir() else []
        if not raw_dir.is_dir():
            errors.append(f"Missing raw directory: {raw_dir}")
        if raw_dir.is_dir() and not detected:
            errors.append(
                "No files matching '*annotations.csv.gz' or "
                "'*filtered_contig_annotations.csv.gz' found."
            )
        return AdapterValidationResult(
            valid=not errors,
            errors=errors,
            warnings=warnings,
            detected_files=detected,
            summary={"raw_dir": str(raw_dir), "n_files": len(detected)},
        )

    @classmethod
    def extract_metadata(cls, file_path: Path) -> dict[str, str]:
        metadata = parse_filename_metadata(file_path.name)
        return {
            "sample_id": metadata["gsm_id"],
            "sample_group": metadata["sample_group"],
            "cell_type": metadata["cell_type"],
            "compartment": metadata["compartment"],
            "patient": metadata["patient"],
        }

    @classmethod
    def normalize(
        cls,
        dataset_path: Path,
        output_path: Path,
        *,
        dataset_id: str = "",
    ) -> Path:
        validation = cls.validate_input(dataset_path)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        dataset_name = _dataset_id(dataset_path, dataset_id)
        frames: list[pd.DataFrame] = []
        for file_path in validation.detected_files:
            metadata = cls.extract_metadata(file_path)
            df = pd.read_csv(file_path, compression="gzip")
            missing = [col for col in TENX_ANNOTATION_COLUMNS if col not in df.columns]
            if missing:
                raise ValueError(
                    f"File {file_path} is missing required columns: {missing}"
                )
            unified = df[TENX_ANNOTATION_COLUMNS].assign(
                dataset_id=dataset_name,
                source_file=file_path.name,
                adapter_name=cls.name,
                adapter_version=cls.version,
                **metadata,
            )
            unified = unified[REQUIRED_COLUMNS]
            frames.append(unified)

        combined = pd.concat(frames, ignore_index=True)
        schema_result = validate_unified_schema(combined)
        if not schema_result.valid:
            raise ValueError("; ".join(schema_result.errors))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(output_path, index=False)
        return output_path

    @classmethod
    def get_output_schema(cls) -> list[str]:
        return list(REQUIRED_COLUMNS)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Normalize a 10x dataset to unified_annotations.csv."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Path to dataset directory containing dataset.yaml and raw/.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: dataset/intermediate/unified_annotations.csv).",
    )
    args = parser.parse_args()
    output = args.output or (
        args.dataset / "intermediate" / "unified_annotations.csv"
    )
    TenXAdapter.normalize(args.dataset, output)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
