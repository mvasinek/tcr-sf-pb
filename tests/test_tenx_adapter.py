"""Tests for TenX adapter."""

from pathlib import Path

import pandas as pd
import pytest

from tcr_bcr_tools.adapters.schema import REQUIRED_COLUMNS, UNIFIED_ANNOTATIONS_FILE
from tcr_bcr_tools.adapters.tenx.adapter import TenXAdapter, find_tenx_annotation_files
from tcr_bcr_tools.metadata import parse_filename_metadata
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


@pytest.fixture
def tenx_dataset(tmp_path: Path) -> Path:
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", source="GEO", adapter="tenx")
    _write_annotation_file(
        dataset.raw_dir
        / "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-1", "TRA", "CAVSDYGQNFVF")],
    )
    _write_annotation_file(
        dataset.raw_dir / "GSM4859842_PM4_CD4_blood_p1_annotations.csv.gz",
        [_sample_row("CELL-2", "TRB", "CASS1")],
    )
    return dataset.root


def test_find_tenx_annotation_files(tenx_dataset: Path) -> None:
    files = find_tenx_annotation_files(tenx_dataset / "raw")
    assert len(files) == 2
    names = {path.name for path in files}
    assert "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz" in names
    assert "GSM4859842_PM4_CD4_blood_p1_annotations.csv.gz" in names


def test_extract_metadata() -> None:
    metadata = TenXAdapter.extract_metadata(
        Path("GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz")
    )
    assert metadata["sample_id"] == "GSM4859841"
    assert metadata["sample_group"] == "PM1"
    assert metadata["cell_type"] == "CD4"
    assert metadata["compartment"] == "SF"
    assert metadata["patient"] == "p7"


def test_parse_filename_metadata_blood() -> None:
    metadata = parse_filename_metadata(
        "GSM4859842_PM4_CD4_blood_p1_filtered_contig_annotations.csv.gz"
    )
    assert metadata["compartment"] == "blood"


def test_tenx_adapter_validate_input(tenx_dataset: Path) -> None:
    result = TenXAdapter.validate_input(tenx_dataset)
    assert result.valid is True
    assert len(result.detected_files) == 2


def test_tenx_adapter_normalize_creates_unified_file(tenx_dataset: Path) -> None:
    output = tenx_dataset / "intermediate" / UNIFIED_ANNOTATIONS_FILE
    TenXAdapter.normalize(tenx_dataset, output, dataset_id="GSE160097")
    assert output.exists()
    df = pd.read_csv(output)
    assert list(df.columns) == REQUIRED_COLUMNS
    assert set(df["dataset_id"]) == {"GSE160097"}
    assert set(df["adapter_name"]) == {"tenx"}


def test_skeleton_adapters_not_implemented() -> None:
    from tcr_bcr_tools.adapters.airr.adapter import AIRRAdapter
    from tcr_bcr_tools.adapters.bdrhapsody.adapter import BDRhapsodyAdapter
    from tcr_bcr_tools.adapters.custom.adapter import CustomAdapter

    for adapter in (BDRhapsodyAdapter, AIRRAdapter, CustomAdapter):
        result = adapter.validate_input(Path("."))
        assert result.valid is False
        assert result.errors == ["Adapter not implemented yet"]
