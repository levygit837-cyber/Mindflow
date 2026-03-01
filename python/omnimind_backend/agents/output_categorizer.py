"""Backward-compatible shim — canonical location: omnimind_backend.runtime.output_categorizer"""

from omnimind_backend.runtime.output_categorizer import (  # noqa: F401
    OutputCategory,
    categorize_output,
)

__all__ = ["OutputCategory", "categorize_output"]
