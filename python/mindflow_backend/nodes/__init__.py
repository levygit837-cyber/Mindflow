"""Node implementations for MindFlow orchestration."""

# Base classes
from mindflow_backend.nodes.base import (
    BaseNode,
    NodeType,
    NodeCategory,
    StatefulNode,
    StreamableNode,
)

# Registry
from mindflow_backend.nodes.registry import (
    NodeRegistry,
    get_node_registry,
    NodeCapability,
    classify_node,
    get_node_label,
    is_streamable_node,
)

# Orchestrator nodes
from mindflow_backend.nodes.implementations.orchestrator import (
    RouteNode,
    ExecuteNode,
    RespondNode,
    DecompositionNode,
)

# Agent nodes (will be implemented)
# from mindflow_backend.nodes.agents import (
#     LLMNode,
#     ToolNode,
#     MemoryNode,
# )

# Control nodes
from mindflow_backend.nodes.implementations.control import (
    ConditionNode,
    MultiConditionNode,
    LoopNode,
    ForEachNode,
    WhileNode,
    DoWhileNode,
    ParallelNode,
    ParallelMapNode,
    ParallelAnyNode,
    ParallelRaceNode,
)

# Integration nodes
from mindflow_backend.nodes.implementations.integration import (
    AgentBridge,
    ToolBridge,
    MemoryBridge,
)

# Processing nodes
from mindflow_backend.nodes.implementations.processing import (
    TransformNode,
    DataMappingNode,
    DataValidationNode,
    FilterNode,
    MultiFilterNode,
    AggregateNode,
    StatisticalAggregateNode,
    GroupByAggregateNode,
)

# I/O nodes
from mindflow_backend.nodes.implementations.io import (
    InputNode,
    StreamInputNode,
    FileInputNode,
    OutputNode,
    StreamOutputNode,
    StreamNode,
    BatchStreamNode,
    SplitStreamNode,
)

# Backward compatibility
from mindflow_backend.runtime.node_registry import (
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
    
    # Control nodes
    "ConditionNode",
    "MultiConditionNode",
    "LoopNode",
    "ForEachNode",
    "WhileNode",
    "DoWhileNode",
    "ParallelNode",
    "ParallelMapNode",
    "ParallelAnyNode",
    "ParallelRaceNode",
    
    # Processing nodes
    "TransformNode",
    "DataMappingNode",
    "DataValidationNode",
    "FilterNode",
    "MultiFilterNode",
    "AggregateNode",
    "StatisticalAggregateNode",
    "GroupByAggregateNode",
    
    # I/O nodes
    "InputNode",
    "StreamInputNode",
    "FileInputNode",
    "OutputNode",
    "StreamOutputNode",
    "StreamNode",
    "BatchStreamNode",
    "SplitStreamNode",
    
    # Integration nodes
    "AgentBridge",
    "ToolBridge",
    "MemoryBridge",
    
    # Backward compatibility
    "RuntimeNodeCategory",
    "runtime_classify_node",
    "runtime_get_node_label",
    "runtime_is_streamable_node",
]
