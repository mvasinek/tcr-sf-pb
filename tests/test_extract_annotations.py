"""Tests for annotation file discovery and combination."""

from pathlib import Path

import pandas as pd
import pytest

from tcr_bcr_tools.extract_annotations import OUTPUT_COLUMNS, combine_annotation_files
from tcr_bcr_tools.io import find_annotation_files

ANNOTATION_COLUMNS = OUTPUT_COLUMNS[6:]


def _write_annotation_file(path: Path, rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    for column in ANNOTATION_COLUMNS:
        if column not in df.columns:
            df[column] = None
    df = df[ANNOTATION_COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")


@pytest.fixture
def sample_rows() -> tuple[list[dict], list[dict]]:
    blood_rows = [
        {
            "barcode": "CELL-1",
            "is_cell": True,
            "contig_id": "CELL-1_contig_1",
            "high_confidence": True,
            "length": 500,
            "chain": "TRA",
            "v_gene": "TRAV1",
            "d_gene": None,
            "j_gene": "TRAJ1",
            "c_gene": "TRAC",
            "full_length": True,
            "productive": True,
            "cdr3": "CAVSDYGQNFVF",
            "cdr3_nt": "TGTGCTGTGAGTGATGATGGGCAATTTTGTGTTT",
            "reads": 100,
            "umis": 5,
            "raw_clonotype_id": "clonotype1",
            "raw_consensus_id": "clonotype1_consensus_1",
        },
        {
            "barcode": "CELL-2",
            "is_cell": True,
            "contig_id": "CELL-2_contig_1",
            "high_confidence": True,
            "length": 480,
            "chain": "Multi",
            "v_gene": "TRBV1",
            "d_gene": None,
            "j_gene": "TRAJ10",
            "c_gene": "TRBC1",
            "full_length": False,
            "productive": None,
            "cdr3": None,
            "cdr3_nt": None,
            "reads": 50,
            "umis": 2,
            "raw_clonotype_id": "clonotype2",
            "raw_consensus_id": None,
        },
    ]
    sf_rows = [
        {
            "barcode": "CELL-3",
            "is_cell": True,
            "contig_id": "CELL-3_contig_1",
            "high_confidence": True,
            "length": 520,
            "chain": "TRB",
            "v_gene": "TRBV2",
            "d_gene": "TRBD1",
            "j_gene": "TRBJ1",
            "c_gene": "TRBC1",
            "full_length": True,
            "productive": True,
            "cdr3": "CASSLGQETQYF",
            "cdr3_nt": "TGTGCCAGCAGCTTGGGGCAGGAGACCCAGTACTTC",
            "reads": 200,
            "umis": 8,
            "raw_clonotype_id": "clonotype3",
            "raw_consensus_id": "clonotype3_consensus_1",
        }
    ]
    return blood_rows, sf_rows


@pytest.fixture
def annotation_input_dir(tmp_path: Path, sample_rows: tuple[list[dict], list[dict]]) -> Path:
    blood_rows, sf_rows = sample_rows
    nested_dir = tmp_path / "nested"
    _write_annotation_file(
        nested_dir / "GSM4859842_PM4_CD4_blood_p1_filtered_contig_annotations.csv.gz",
        blood_rows,
    )
    _write_annotation_file(
        tmp_path / "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        sf_rows,
    )
    (tmp_path / "ignore_me.txt").write_text("not an annotation file", encoding="utf-8")
    return tmp_path


def test_find_annotation_files(annotation_input_dir: Path) -> None:
    files = find_annotation_files(annotation_input_dir)
    names = [path.name for path in files]
    assert names == [
        "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        "GSM4859842_PM4_CD4_blood_p1_filtered_contig_annotations.csv.gz",
    ]


def test_combine_annotation_files(annotation_input_dir: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "combined_annotations.csv"
    combine_annotation_files(annotation_input_dir, output_path)

    result = pd.read_csv(output_path)
    assert list(result.columns) == OUTPUT_COLUMNS
    assert len(result) == 3
    assert set(result["compartment"]) == {"SF", "blood"}
    assert set(result["source_file"]) == {
        "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        "GSM4859842_PM4_CD4_blood_p1_filtered_contig_annotations.csv.gz",
    }


def test_combine_annotation_files_productive_only(
    annotation_input_dir: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "combined_annotations_productive.csv"
    combine_annotation_files(
        annotation_input_dir, output_path, productive_only=True
    )

    result = pd.read_csv(output_path)
    assert len(result) == 2
    assert set(result["chain"]) == {"TRA", "TRB"}
    assert result["cdr3"].notna().all()
    assert (result["is_cell"] == True).all()  # noqa: E712
    assert (result["high_confidence"] == True).all()  # noqa: E712
    assert (result["full_length"] == True).all()  # noqa: E712
    assert (result["productive"] == True).all()  # noqa: E712
