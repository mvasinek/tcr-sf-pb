"""Shared GUI constants."""

from __future__ import annotations

PIPELINE_STEPS = [
    ("extract_annotations", "Extract annotations"),
    ("unified_table", "Unified table"),
    ("paired_detection", "Detection"),
    ("expansion", "Expansion"),
    ("roc_auc", "ROC"),
    ("decile_information", "Heatmap"),
]

FUTURE_ANALYSES = [
    "Detection curves",
    "Expansion",
    "Threshold sweep",
    "Rank concordance",
    "ROC/AUC",
    "Regression",
    "Decile information",
]

STATUS_LABELS = {
    "done": ("✔", "green"),
    "pending": ("Pending", "orange"),
    "failed": ("Failed", "red"),
    "running": ("Running", "blue"),
}

ADAPTER_OPTIONS = ["tenx", "bdrhapsody", "airr", "custom"]

DEFAULT_WORKSPACE_NAME = "tcr-sf-pb-workspace"

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
)
