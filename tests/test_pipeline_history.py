"""Tests for pipeline run history and logging."""

from pathlib import Path

import yaml

from tcr_bcr_tools.pipeline.history import (
    append_history_record,
    append_pipeline_log,
    load_history,
    read_pipeline_log,
    save_history,
)


def test_history_roundtrip(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    record = {
        "step": "extract_annotations",
        "started": "2026-06-14T10:00:00",
        "finished": "2026-06-14T10:00:05",
        "duration": 5.0,
        "status": "completed",
        "tool_version": "0.5.2",
        "outputs": {"csv": ["datasets/demo/intermediate/combined_annotations.csv"]},
        "git_branch": "main",
        "git_commit": "abc123",
        "git_tag": "v0.5.2",
    }
    append_history_record(logs_dir, record)
    loaded = load_history(logs_dir)
    assert len(loaded) == 1
    assert loaded[0]["step"] == "extract_annotations"
    assert loaded[0]["git_commit"] == "abc123"


def test_history_serialization(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    records = [
        {"step": "a", "status": "completed"},
        {"step": "b", "status": "failed"},
    ]
    save_history(logs_dir, records)
    raw = yaml.safe_load((logs_dir / "run_history.yaml").read_text(encoding="utf-8"))
    assert raw == {"runs": records}
    assert load_history(logs_dir) == records


def test_pipeline_log_append_and_filter(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    append_pipeline_log(logs_dir, "extract_annotations", "INFO", "Starting step")
    append_pipeline_log(logs_dir, "extract_annotations", "ERROR", "Failed")
    append_pipeline_log(logs_dir, "roc_auc", "WARNING", "Low sample count")

    all_entries = read_pipeline_log(logs_dir, tail=200, level="All")
    assert len(all_entries) == 3

    error_entries = read_pipeline_log(logs_dir, tail=200, level="Error")
    assert len(error_entries) == 1
    assert error_entries[0]["message"] == "Failed"

    info_entries = read_pipeline_log(logs_dir, tail=200, level="Info")
    assert len(info_entries) == 1
    assert info_entries[0]["level"] == "INFO"
