"""Shared GUI constants."""

from __future__ import annotations

STATUS_LABELS = {
    "completed": ("✔", "green"),
    "done": ("✔", "green"),
    "pending": ("○", "orange"),
    "failed": ("✖", "red"),
    "running": ("⟳", "blue"),
    "skipped": ("⊘", "gray"),
}

ADAPTER_OPTIONS = ["tenx", "bdrhapsody", "airr", "custom"]

DEFAULT_WORKSPACE_NAME = "tcr-sf-pb-workspace"

LOG_LEVEL_FILTERS = ["All", "Info", "Warning", "Error"]

RESULTS_ANALYSES = [
    ("Detection", "detection_curves"),
    ("Expansion", "expansion_concordance"),
    ("Threshold sweep", "threshold_sweep"),
    ("Rank", "rank_concordance"),
    ("Regression", "correlation_regression"),
    ("ROC", "roc_auc"),
    ("Heatmap", "decile_information"),
    ("Validation", "validate_dataset"),
    ("Reports", "reports"),
]

SESSION_KEYS = (
    "workspace_path",
    "workspace",
    "selected_project",
    "selected_dataset",
    "show_create_project",
    "show_register_dataset",
    "show_settings",
    "show_logs",
    "show_about",
    "selected_pipeline_step",
    "force_recompute",
    "show_results",
    "selected_results_analysis",
    "selected_output_id",
    "results_search_query",
    "compare_output_a",
    "compare_output_b",
)
