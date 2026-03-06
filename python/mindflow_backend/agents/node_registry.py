"""Backward-compatible shim — canonical location: mindflow_backend.runtime.node_registry"""

from mindflow_backend.runtime.node_registry import (  # noqa: F401
    NodeCategory,
    classify_node,
    get_node_label,
    is_streamable_node,
)

__all__ = ["NodeCategory", "classify_node", "get_node_label", "is_streamable_node"]
