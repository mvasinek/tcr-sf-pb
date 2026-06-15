"""JSON preview helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_data(path: Path) -> Any:
    """Load JSON file contents."""
    return json.loads(path.read_text(encoding="utf-8"))
