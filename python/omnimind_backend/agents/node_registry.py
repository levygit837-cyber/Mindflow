"""Backward-compatible shim — canonical location: omnimind_backend.runtime.node_registry"""

from omnimind_backend.runtime.node_registry import (  # noqa: F401
    NodeCategory,
    classify_node,
    get_node_label,
    is_streamable_node,
)

__all__ = ["NodeCategory", "classify_node", "get_node_label", "is_streamable_node"]
