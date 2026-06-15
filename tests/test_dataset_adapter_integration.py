"""Tests for Dataset adapter integration."""

from pathlib import Path

import pandas as pd

from tcr_bcr_tools.adapters.schema import ADAPTER_REPORT_FILE, UNIFIED_ANNOTATIONS_FILE
from tcr_bcr_tools.project import Workspace
from tcr_bcr_tools.project.manifest import load_yaml

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


def _write_annotation_file(path: Path, rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    for column in ANNOTATION_COLUMNS:
        if column not in df.columns:
            df[column] = None
    df = df[ANNOTATION_COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")


def _sample_row(barcode: str, chain: str, cdr3: str) -> dict:
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
        "cdr3_nt": "TGTGCTGTGAGTGATGATGGGCAATTTTGTGTTT",
        "reads": 100,
        "umis": 5,
        "raw_clonotype_id": "clonotype1",
        "raw_consensus_id": "clonotype1_consensus_1",
    }


def test_dataset_get_adapter(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", adapter="tenx")
    adapter_cls = dataset.get_adapter()
    assert adapter_cls.name == "tenx"


def test_dataset_validate_with_adapter(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", adapter="tenx")
    _write_annotation_file(
        dataset.raw_dir
        / "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-1", "TRA", "CAVSDYGQNFVF")],
    )
    result = dataset.validate_with_adapter()
    assert result.valid is True
    assert len(result.detected_files) == 1


def test_dataset_normalize_with_adapter_writes_report(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", adapter="tenx")
    _write_annotation_file(
        dataset.raw_dir
        / "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-1", "TRA", "CAVSDYGQNFVF")],
    )
    output = dataset.normalize_with_adapter()
    assert output.name == UNIFIED_ANNOTATIONS_FILE
    assert dataset.has_unified_annotations() is True

    report_path = dataset.intermediate_dir / ADAPTER_REPORT_FILE
    assert report_path.exists()
    report = load_yaml(report_path)
    assert report["adapter"]["name"] == "tenx"
    assert report["run"]["status"] == "completed"
    assert report["output"]["n_rows"] == 1
