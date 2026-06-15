"""Tests for pipeline validation integration."""

from pathlib import Path

import pandas as pd
import pytest

from tcr_bcr_tools.pipeline import PipelineRunner
from tcr_bcr_tools.pipeline.runner import ValidationGateError
from tcr_bcr_tools.pipeline.step import COMPLETED
from tcr_bcr_tools.project import Workspace


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
        "cdr3_nt": "TGT",
        "reads": 100,
        "umis": 5,
        "raw_clonotype_id": "clonotype1",
        "raw_consensus_id": "clonotype1_consensus_1",
    }


@pytest.fixture
def pipeline_workspace(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.load()
    dataset = workspace.create_dataset("GSE160097", source="GEO", adapter="tenx")
    raw_dir = dataset.raw_dir
    _write_annotation_file(
        raw_dir / "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-1", "TRA", "CAVSDYGQNFVF"), _sample_row("CELL-1", "TRB", "CASS1")],
    )
    _write_annotation_file(
        raw_dir / "GSM4859842_PM4_CD4_blood_p1_filtered_contig_annotations.csv.gz",
        [_sample_row("CELL-2", "TRA", "CAVSDYGQNFVF"), _sample_row("CELL-2", "TRB", "CASS1")],
    )
    project = workspace.create_project(
        "JIA_Pilot",
        name="JIA Pilot",
        datasets=["GSE160097"],
        adapter="tenx",
    )
    return workspace, project


def test_validate_dataset_step(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project, repo_root=Path(__file__).resolve().parents[1])
    result = runner.run_step("validate_dataset")
    assert result["status"] == COMPLETED
    assert project.get_pipeline_status("validate_dataset") == COMPLETED


def test_pipeline_blocks_without_validation(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project, repo_root=Path(__file__).resolve().parents[1])
    with pytest.raises(ValidationGateError):
        runner.run_step("extract_annotations")


def test_pipeline_allows_warnings(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project, repo_root=Path(__file__).resolve().parents[1])
    runner.run_step("validate_dataset")
    allowed, _reason = runner.check_validation_gate("extract_annotations")
    assert allowed is True
