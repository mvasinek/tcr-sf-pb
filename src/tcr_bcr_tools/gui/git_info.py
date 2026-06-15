"""Read-only Git metadata for the status bar."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_available(repo_root: Path | None = None) -> bool:
    """Return True if the path is inside a Git repository."""
    return _run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_root) == "true"


def get_current_branch(repo_root: Path | None = None) -> str:
    """Return current Git branch or 'unknown'."""
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    return branch or "unknown"


def get_last_commit(repo_root: Path | None = None) -> str:
    """Return short hash of HEAD or 'unknown'."""
    commit = _run_git(["rev-parse", "--short", "HEAD"], cwd=repo_root)
    return commit or "unknown"


def get_current_tag(repo_root: Path | None = None) -> str:
    """Return nearest tag on HEAD or 'unknown'."""
    tag = _run_git(["describe", "--tags", "--exact-match"], cwd=repo_root)
    if tag:
        return tag
    describe = _run_git(["describe", "--tags", "--always"], cwd=repo_root)
    return describe or "unknown"


def get_git_summary(repo_root: Path | None = None) -> dict[str, str]:
    """Return branch, commit, and tag for display."""
    if not git_available(repo_root):
        return {
            "available": "false",
            "branch": "Git unavailable",
            "commit": "Git unavailable",
            "tag": "Git unavailable",
        }
    return {
        "available": "true",
        "branch": get_current_branch(repo_root),
        "commit": get_last_commit(repo_root),
        "tag": get_current_tag(repo_root),
    }
