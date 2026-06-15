"""Registry of available pipeline steps and their callables."""

from __future__ import annotations

from pathlib import Path

from tcr_bcr_tools import __version__
from tcr_bcr_tools.build_clonotypes import build_clonotype_tables
from tcr_bcr_tools.build_detection_table import build_detection_table
from tcr_bcr_tools.correlation_regression import run_correlation_regression
from tcr_bcr_tools.decile_information import run_decile_information_analysis
from tcr_bcr_tools.detection_curves import run_detection_curve_analysis
from tcr_bcr_tools.expansion_concordance import run_expansion_concordance_analysis
from tcr_bcr_tools.adapters.schema import UNIFIED_ANNOTATIONS_FILE, ensure_legacy_annotation_columns
from tcr_bcr_tools.pipeline.step import PipelineContext, PipelineStep
from tcr_bcr_tools.rank_concordance import run_rank_concordance
from tcr_bcr_tools.roc_auc_analysis import run_roc_auc_cli
from tcr_bcr_tools.threshold_sweep import run_threshold_sweep_cli
from tcr_bcr_tools.weighted_rank_concordance import run_weighted_rank_concordance

STEP_ORDER = [
    "extract_annotations",
    "build_unified_table",
    "build_detection_table",
    "detection_curves",
    "expansion_concordance",
    "threshold_sweep",
    "rank_concordance",
    "weighted_rank",
    "correlation_regression",
    "roc_auc",
    "decile_information",
]


def _workspace_relative(workspace_root: Path, path: Path) -> str:
    return str(path.relative_to(workspace_root))


def _paths_from_files(workspace_root: Path, *paths: Path) -> dict[str, list[str]]:
    csv_files: list[str] = []
    png_files: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        rel = _workspace_relative(workspace_root, path)
        if path.suffix.lower() == ".csv":
            csv_files.append(rel)
        elif path.suffix.lower() in {".png", ".pdf", ".svg"}:
            png_files.append(rel)
    return {"csv": csv_files, "png": png_files}


def _collect_dir_outputs(workspace_root: Path, output_dir: Path) -> dict[str, list[str]]:
    csv_files: list[str] = []
    png_files: list[str] = []
    if not output_dir.is_dir():
        return {"csv": csv_files, "png": png_files}
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = _workspace_relative(workspace_root, path)
        if path.suffix.lower() == ".csv":
            csv_files.append(rel)
        elif path.suffix.lower() in {".png", ".pdf", ".svg"}:
            png_files.append(rel)
    return {"csv": csv_files, "png": png_files}


def _run_extract_annotations(ctx: PipelineContext) -> dict[str, list[str]]:
    output_path = ctx.dataset.normalize_with_adapter()
    report_path = ctx.intermediate_dir / "adapter_report.yaml"
    return _paths_from_files(ctx.workspace.root, output_path, report_path)


def _run_build_unified_table(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.intermediate_dir / UNIFIED_ANNOTATIONS_FILE
    cell_output = ctx.intermediate_dir / "cell_receptors.csv"
    clone_output = ctx.intermediate_dir / "clone_counts.csv"
    build_clonotype_tables(input_path, cell_output, clone_output)
    return _paths_from_files(ctx.workspace.root, cell_output, clone_output)


def _run_build_detection_table(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.intermediate_dir / "clone_counts.csv"
    output_path = ctx.outputs_dir / "paired_detection_table.csv"
    build_detection_table(input_path, output_path)
    return _paths_from_files(ctx.workspace.root, output_path)


def _run_detection_curves(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.outputs_dir / "paired_detection_table.csv"
    output_dir = ctx.outputs_dir / "detection_curves"
    run_detection_curve_analysis(input_path, output_dir)
    return _collect_dir_outputs(ctx.workspace.root, output_dir)


def _run_expansion_concordance(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.outputs_dir / "paired_detection_table.csv"
    output_dir = ctx.outputs_dir / "expansion_concordance"
    run_expansion_concordance_analysis(input_path, output_dir)
    return _collect_dir_outputs(ctx.workspace.root, output_dir)


def _run_threshold_sweep(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.outputs_dir / "paired_detection_table.csv"
    output_dir = ctx.outputs_dir / "threshold_sweep"
    run_threshold_sweep_cli(input_path, output_dir)
    return _collect_dir_outputs(ctx.workspace.root, output_dir)


def _run_rank_concordance(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.outputs_dir / "paired_detection_table.csv"
    output_dir = ctx.outputs_dir / "rank_concordance"
    run_rank_concordance(input_path, output_dir)
    return _collect_dir_outputs(ctx.workspace.root, output_dir)


def _run_weighted_rank(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.outputs_dir / "rank_concordance" / "rank_table.csv"
    output_dir = ctx.outputs_dir / "weighted_rank"
    run_weighted_rank_concordance(input_path, output_dir)
    return _collect_dir_outputs(ctx.workspace.root, output_dir)


def _run_correlation_regression(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.outputs_dir / "paired_detection_table.csv"
    output_dir = ctx.outputs_dir / "correlation_regression"
    run_correlation_regression(input_path, output_dir)
    return _collect_dir_outputs(ctx.workspace.root, output_dir)


def _run_roc_auc(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.outputs_dir / "paired_detection_table.csv"
    output_dir = ctx.outputs_dir / "roc_auc"
    run_roc_auc_cli(input_path, output_dir)
    return _collect_dir_outputs(ctx.workspace.root, output_dir)


def _run_decile_information(ctx: PipelineContext) -> dict[str, list[str]]:
    input_path = ctx.outputs_dir / "paired_detection_table.csv"
    output_dir = ctx.outputs_dir / "decile_information"
    run_decile_information_analysis(input_path, output_dir)
    return _collect_dir_outputs(ctx.workspace.root, output_dir)


def _build_registry() -> dict[str, PipelineStep]:
    steps = [
        PipelineStep(
            id="extract_annotations",
            name="Extract annotations",
            description="Normalize raw dataset inputs to unified_annotations.csv via adapter.",
            version=__version__,
            dependencies=[],
            callable=_run_extract_annotations,
            output_directory="intermediate",
        ),
        PipelineStep(
            id="build_unified_table",
            name="Unified table",
            description="Build cell receptor and clone count tables from combined annotations.",
            version=__version__,
            dependencies=["extract_annotations"],
            callable=_run_build_unified_table,
            output_directory="intermediate",
        ),
        PipelineStep(
            id="build_detection_table",
            name="Detection table",
            description="Build paired SF/blood clone detection table from clone counts.",
            version=__version__,
            dependencies=["build_unified_table"],
            callable=_run_build_detection_table,
            output_directory="outputs",
        ),
        PipelineStep(
            id="detection_curves",
            name="Detection curves",
            description="Summarize detection probability by clone size bin.",
            version=__version__,
            dependencies=["build_detection_table"],
            callable=_run_detection_curves,
            output_directory="detection_curves",
        ),
        PipelineStep(
            id="expansion_concordance",
            name="Expansion concordance",
            description="Compare SF and blood expansion status at a fixed threshold.",
            version=__version__,
            dependencies=["build_detection_table"],
            callable=_run_expansion_concordance,
            output_directory="expansion_concordance",
        ),
        PipelineStep(
            id="threshold_sweep",
            name="Threshold sweep",
            description="Sweep expansion thresholds and summarize concordance.",
            version=__version__,
            dependencies=["build_detection_table"],
            callable=_run_threshold_sweep,
            output_directory="threshold_sweep",
        ),
        PipelineStep(
            id="rank_concordance",
            name="Rank concordance",
            description="Compare SF and blood clone ranks and percentiles.",
            version=__version__,
            dependencies=["build_detection_table"],
            callable=_run_rank_concordance,
            output_directory="rank_concordance",
        ),
        PipelineStep(
            id="weighted_rank",
            name="Weighted rank",
            description="Weighted rank concordance using rank table outputs.",
            version=__version__,
            dependencies=["rank_concordance"],
            callable=_run_weighted_rank,
            output_directory="weighted_rank",
        ),
        PipelineStep(
            id="correlation_regression",
            name="Correlation regression",
            description="Correlation and regression between SF and blood abundances.",
            version=__version__,
            dependencies=["build_detection_table"],
            callable=_run_correlation_regression,
            output_directory="correlation_regression",
        ),
        PipelineStep(
            id="roc_auc",
            name="ROC / AUC",
            description="ROC and AUC analysis for expansion prediction.",
            version=__version__,
            dependencies=["build_detection_table"],
            callable=_run_roc_auc,
            output_directory="roc_auc",
        ),
        PipelineStep(
            id="decile_information",
            name="Decile information",
            description="Decile-based information content of abundance predictors.",
            version=__version__,
            dependencies=["build_detection_table"],
            callable=_run_decile_information,
            output_directory="decile_information",
        ),
    ]
    return {step.id: step for step in steps}


_REGISTRY: dict[str, PipelineStep] | None = None


def get_registry() -> dict[str, PipelineStep]:
    """Return the global pipeline step registry."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def list_steps() -> list[PipelineStep]:
    """Return pipeline steps in execution order."""
    registry = get_registry()
    return [registry[step_id] for step_id in STEP_ORDER if step_id in registry]


def get_step(step_id: str) -> PipelineStep:
    """Return one registered step by id."""
    registry = get_registry()
    if step_id not in registry:
        raise KeyError(f"Unknown pipeline step: {step_id}")
    return registry[step_id]
