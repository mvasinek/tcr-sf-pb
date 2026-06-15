"""Clone-size bin definitions shared across analysis modules."""

from __future__ import annotations

CLONE_SIZE_BINS: list[tuple[str, int, int | None]] = [
    ("1", 1, 1),
    ("2", 2, 2),
    ("3-5", 3, 5),
    ("6-10", 6, 10),
    ("11-20", 11, 20),
    ("21-50", 21, 50),
    ("51-100", 51, 100),
    ("101+", 101, None),
]


def assign_clone_size_bin(source_cells: int) -> tuple[str, int, int | None]:
    """Assign a clone-size bin label and bounds for ``source_cells``."""
    for label, bin_min, bin_max in CLONE_SIZE_BINS:
        if bin_max is None:
            if source_cells >= bin_min:
                return label, bin_min, bin_max
        elif bin_min <= source_cells <= bin_max:
            return label, bin_min, bin_max
    raise ValueError(f"Could not assign clone-size bin for source_cells={source_cells}")
