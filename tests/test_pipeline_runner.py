"""Tests for pipeline runner execution."""

from pathlib import Path

import pandas as pd
import pytest

from tcr_bcr_tools.pipeline import PipelineRunner
from tcr_bcr_tools.pipeline.history import load_history, read_pipeline_log
from tcr_bcr_tools.pipeline.runner import DependencyError, ValidationGateError
from tcr_bcr_tools.pipeline.step import COMPLETED, SKIPPED
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
def pipeline_workspace(tmp_path: Path) -> tuple[Workspace, object]:
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


def test_validate_dependencies(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project)
    ok, missing = runner.validate_dependencies("build_unified_table")
    assert ok is False
    assert "validate_dataset" in missing


def test_dependency_error_on_run_step(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project)
    with pytest.raises(ValidationGateError):
        runner.run_step("build_detection_table")


def test_run_extract_annotations(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project, repo_root=Path(__file__).resolve().parents[1])
    runner.run_step("validate_dataset")
    result = runner.run_step("extract_annotations")
    assert result["status"] == COMPLETED
    assert result["outputs"]["csv"]
    manifest = load_yaml(project.manifest_path)
    assert manifest["pipeline"]["extract_annotations"]["status"] == COMPLETED
    assert manifest["outputs"]["extract_annotations"]["csv"]
    history = load_history(project.logs_dir)
    assert history[-1]["step"] == "extract_annotations"
    assert history[-1]["git_branch"] in {"main", "unknown"}
    logs = read_pipeline_log(project.logs_dir)
    assert any(entry["step"] == "extract_annotations" for entry in logs)


def test_skip_completed_step(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project, repo_root=Path(__file__).resolve().parents[1])
    runner.run_step("validate_dataset")
    first = runner.run_step("extract_annotations")
    assert first["status"] == COMPLETED
    second = runner.run_step("extract_annotations")
    assert second["status"] == SKIPPED


def test_force_recompute(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project, repo_root=Path(__file__).resolve().parents[1])
    runner.run_step("validate_dataset")
    runner.run_step("extract_annotations")
    forced = PipelineRunner(
        workspace,
        project,
        force_recompute=True,
        repo_root=Path(__file__).resolve().parents[1],
    )
    result = forced.run_step("extract_annotations")
    assert result["status"] == COMPLETED


def test_needs_recompute_missing_outputs(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project)
    project.set_pipeline_step("extract_annotations", COMPLETED)
    project.set_step_outputs(
        "extract_annotations",
        {"csv": ["datasets/missing/intermediate/combined_annotations.csv"]},
    )
    assert runner.needs_recompute("extract_annotations") is True


def test_run_pipeline_skips_completed(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project, repo_root=Path(__file__).resolve().parents[1])
    runner.run_step("validate_dataset")
    results = runner.run()
    assert results[0]["status"] == SKIPPED
    assert results[0]["step_id"] == "validate_dataset"


def test_output_registry_load(pipeline_workspace) -> None:
    workspace, project = pipeline_workspace
    runner = PipelineRunner(workspace, project, repo_root=Path(__file__).resolve().parents[1])
    runner.run_step("validate_dataset")
    runner.run_step("extract_annotations")
    legacy_registry = project.get_output_registry()
    assert "extract_annotations" in legacy_registry
    indexed = project.output_registry(workspace.root).list_outputs()
    assert indexed
