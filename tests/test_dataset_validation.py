"""Tests for Dataset validation API."""

from pathlib import Path

import pandas as pd

from tcr_bcr_tools.adapters.schema import REQUIRED_COLUMNS
from tcr_bcr_tools.project import Workspace
from tcr_bcr_tools.validation.report import VALIDATION_REPORT_FILE, VALIDATION_SUMMARY_FILE


def _write_annotation_file(path: Path, rows: list[dict]) -> None:
    columns = [
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
    df = pd.DataFrame(rows)
    for column in columns:
        if column not in df.columns:
            df[column] = None
    df = df[columns]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")


def _sample_row(barcode: str, chain: str, cdr3: str, compartment: str) -> dict:
    return {
        "barcode": barcode,
        "is_cell": True,
        "contig_id": f"{barcode}_contig_1",
        "high_confidence": True,
        "length": 500,
        "chain": chain,
        "v_gene": "TRAV1",
        "d_gene": None,
        "j_gene": "TRAJ1",
        "c_gene": "TRAC",
        "full_length": True,
        "productive": True,
        "cdr3": cdr3,
        "cdr3_nt": "TGT",
        "reads": 100,
        "umis": 5,
        "raw_clonotype_id": "clonotype1",
        "raw_consensus_id": "clonotype1_consensus_1",
    }


def test_dataset_validate_returns_report(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", adapter="tenx")
    _write_annotation_file(
        dataset.raw_dir
        / "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-1", "TRA", "CAVSDYGQNFVF", "SF")],
    )
    _write_annotation_file(
        dataset.raw_dir
        / "GSM4859842_PM4_CD4_blood_p1_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-2", "TRB", "CASS1", "blood")],
    )

    report = dataset.validate(repo_root=Path(__file__).resolve().parents[1])
    assert report.summary.score >= 0
    assert (dataset.intermediate_dir / VALIDATION_REPORT_FILE).exists()
    assert (dataset.intermediate_dir / VALIDATION_SUMMARY_FILE).exists()
    assert dataset.validation_score() == report.summary.score
    assert dataset.last_validation()["critical"] == report.summary.critical


def test_dataset_is_valid_when_clean(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", adapter="tenx")
    _write_annotation_file(
        dataset.raw_dir
        / "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-1", "TRA", "CAVSDYGQNFVF", "SF")],
    )
    _write_annotation_file(
        dataset.raw_dir
        / "GSM4859842_PM4_CD4_blood_p1_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-2", "TRB", "CASS1", "blood")],
    )
    dataset.validate(repo_root=Path(__file__).resolve().parents[1])
    assert dataset.is_valid() is True
