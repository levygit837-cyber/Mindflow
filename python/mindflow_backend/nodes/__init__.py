"""Node implementations for MindFlow orchestration."""

# Base classes
from mindflow_backend.nodes.base import (
    BaseNode,
    NodeCategory,
    NodeType,
    StatefulNode,
    StreamableNode,
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
    DoWhileNode,
    ForEachNode,
    LoopNode,
    MultiConditionNode,
    ParallelAnyNode,
    ParallelMapNode,
    ParallelNode,
    ParallelRaceNode,
    WhileNode,
)

# Integration nodes
from mindflow_backend.nodes.implementations.integration import (
    AgentBridge,
    MemoryBridge,
    ToolBridge,
)

# I/O nodes
from mindflow_backend.nodes.implementations.io import (
    BatchStreamNode,
    FileInputNode,
    InputNode,
    OutputNode,
    SplitStreamNode,
    StreamInputNode,
    StreamNode,
    StreamOutputNode,
)

# Orchestrator nodes
from mindflow_backend.nodes.implementations.orchestrator import (
    DecompositionNode,
    ExecuteNode,
    RespondNode,
    RouteNode,
)

# Processing nodes
from mindflow_backend.nodes.implementations.processing import (
    AggregateNode,
    DataMappingNode,
    DataValidationNode,
    FilterNode,
    GroupByAggregateNode,
    MultiFilterNode,
    StatisticalAggregateNode,
    TransformNode,
)

# Registry
from mindflow_backend.nodes.registry import (
    NodeCapability,
    NodeRegistry,
    classify_node,
    get_node_label,
    get_node_registry,
    is_streamable_node,
)

# Backward compatibility
from mindflow_backend.runtime.node_registry import (
    NodeCategory as RuntimeNodeCategory,
)
from mindflow_backend.runtime.node_registry import (
    classify_node as runtime_classify_node,
)
from mindflow_backend.runtime.node_registry import (
    get_node_label as runtime_get_node_label,
)
from mindflow_backend.runtime.node_registry import (
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
