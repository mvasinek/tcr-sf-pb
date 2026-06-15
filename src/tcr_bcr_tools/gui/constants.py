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
)
