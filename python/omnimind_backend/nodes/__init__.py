"""Node implementations for OmniMind orchestration."""

# Base classes
from omnimind_backend.nodes.base import (
    BaseNode,
    NodeType,
    NodeCategory,
    StatefulNode,
    StreamableNode,
)

# Registry
from omnimind_backend.nodes.registry import (
    NodeRegistry,
    get_node_registry,
    NodeCapability,
    classify_node,
    get_node_label,
    is_streamable_node,
)

# Orchestrator nodes
from omnimind_backend.nodes.orchestrator import (
    RouteNode,
    ExecuteNode,
    RespondNode,
    DecompositionNode,
)

# Agent nodes (will be implemented)
# from omnimind_backend.nodes.agents import (
#     LLMNode,
#     ToolNode,
#     MemoryNode,
# )

# Control nodes (will be implemented)
# from omnimind_backend.nodes.control import (
#     ConditionNode,
#     LoopNode,
#     ParallelNode,
# )

# Backward compatibility
from omnimind_backend.runtime.node_registry import (
    NodeCategory as RuntimeNodeCategory,
    classify_node as runtime_classify_node,
    get_node_label as runtime_get_node_label,
    is_streamable_node as runtime_is_streamable_node,
)

__all__ = [
    # Base classes
    "BaseNode",
    "NodeType",
    "NodeCategory",
    "StatefulNode",
    "StreamableNode",
    
    # Registry
    "NodeRegistry",
    "get_node_registry",
    "NodeCapability",
    "classify_node",
    "get_node_label",
    "is_streamable_node",
    
    # Orchestrator nodes
    "RouteNode",
    "ExecuteNode",
    "RespondNode",
    "DecompositionNode",
    
    # Backward compatibility
    "RuntimeNodeCategory",
    "runtime_classify_node",
    "runtime_get_node_label",
    "runtime_is_streamable_node",
]
