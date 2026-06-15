"""Pipeline run history and log persistence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

RUN_HISTORY_FILE = "run_history.yaml"
PIPELINE_LOG_FILE = "pipeline.log"


def _history_path(logs_dir: Path) -> Path:
    return logs_dir / RUN_HISTORY_FILE


def load_history(logs_dir: Path) -> list[dict[str, Any]]:
    """Load run history records from disk."""
    path = _history_path(logs_dir)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        runs = data.get("runs", [])
        if isinstance(runs, list):
            return runs
    return []


def save_history(logs_dir: Path, records: list[dict[str, Any]]) -> None:
    """Persist run history records to disk."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = _history_path(logs_dir)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {"runs": records},
            handle,
            sort_keys=False,
            default_flow_style=False,
        )


def append_history_record(logs_dir: Path, record: dict[str, Any]) -> None:
    """Append one run record to history."""
    records = load_history(logs_dir)
    records.append(record)
    save_history(logs_dir, records)


def append_pipeline_log(
    logs_dir: Path,
    step: str,
    level: str,
    message: str,
) -> None:
    """Append one line to pipeline.log."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"{timestamp}\t{step}\t{level}\t{message}\n"
    with (_history_path(logs_dir).parent / PIPELINE_LOG_FILE).open(
        "a", encoding="utf-8"
    ) as handle:
        handle.write(line)


def read_pipeline_log(
    logs_dir: Path,
    *,
    tail: int = 200,
    level: str | None = None,
) -> list[dict[str, str]]:
    """Return the last ``tail`` log entries, optionally filtered by level."""
    path = logs_dir / PIPELINE_LOG_FILE
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    entries: list[dict[str, str]] = []
    for line in lines[-tail:]:
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        timestamp, step_id, log_level, message = parts
        if level and level.lower() != "all" and log_level.lower() != level.lower():
            continue
        entries.append(
            {
                "timestamp": timestamp,
                "step": step_id,
                "level": log_level,
                "message": message,
            }
        )
    return entries
