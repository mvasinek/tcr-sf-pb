"""Dataset format adapters."""

from tcr_bcr_tools.adapters.base import (
    AdapterNotFoundError,
    AdapterValidationResult,
    BaseAdapter,
)
from tcr_bcr_tools.adapters.registry import get_adapter, list_adapters, register_adapter
from tcr_bcr_tools.adapters.schema import (
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    UNIFIED_ANNOTATIONS_FILE,
)
from tcr_bcr_tools.adapters.validation import validate_unified_schema

__all__ = [
    "AdapterNotFoundError",
    "AdapterValidationResult",
    "BaseAdapter",
    "OPTIONAL_COLUMNS",
    "REQUIRED_COLUMNS",
    "UNIFIED_ANNOTATIONS_FILE",
    "get_adapter",
    "list_adapters",
    "register_adapter",
    "validate_unified_schema",
]
