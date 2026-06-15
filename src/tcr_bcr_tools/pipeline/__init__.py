"""Pipeline execution engine and registry."""

from tcr_bcr_tools.pipeline.history import (
    append_history_record,
    append_pipeline_log,
    load_history,
    read_pipeline_log,
    save_history,
)
from tcr_bcr_tools.pipeline.registry import STEP_ORDER, get_registry, get_step, list_steps
from tcr_bcr_tools.pipeline.runner import DependencyError, ValidationGateError, PipelineRunner
from tcr_bcr_tools.pipeline.step import (
    COMPLETED,
    FAILED,
    PENDING,
    RUNNING,
    SKIPPED,
    PipelineContext,
    PipelineStep,
)

__all__ = [
    "COMPLETED",
    "FAILED",
    "PENDING",
    "RUNNING",
    "SKIPPED",
    "DependencyError",
    "ValidationGateError",
    "PipelineContext",
    "PipelineRunner",
    "PipelineStep",
    "STEP_ORDER",
    "append_history_record",
    "append_pipeline_log",
    "get_registry",
    "get_step",
    "list_steps",
    "load_history",
    "read_pipeline_log",
    "save_history",
]
