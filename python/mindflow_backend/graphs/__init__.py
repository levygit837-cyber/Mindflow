"""Graph orchestration for MindFlow."""

# Base classes
from mindflow_backend.graphs.base import (
    BaseGraph,
    GraphConfig,
    GraphState,
    GraphType,
    NodeConnection,
    StateManager,
)

# Factory
from mindflow_backend.graphs.factory import (
    GraphFactory,
    build_simple_orchestrator_flow,
    create_orchestrator_graph,
    get_graph_factory,
)

# Orchestrator implementations
from mindflow_backend.graphs.implementations.orchestrator import (
    DecompositionGraph,
    MultiAgentGraph,
    SimpleOrchestratorGraph,
)

# Backward compatibility
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import (
    OrchestratorState,
    SimpleOrchestratorGraph,
    build_simple_orchestrator_flow,
)

# Workflow graphs
from mindflow_backend.graphs.implementations.workflow import (
    ConditionalWorkflowGraph,
    ParallelWorkflowGraph,
    SequentialWorkflowGraph,
)

__all__ = [
    # Base classes
    "BaseGraph",
    "GraphType",
    "GraphState", 
    "StateManager",
    "GraphConfig",
    "NodeConnection",
    
    # Orchestrator graphs
    "SimpleOrchestratorGraph",
    "MultiAgentGraph",
    "DecompositionGraph",
    
    # Factory
    "GraphFactory",
    "get_graph_factory",
    "create_orchestrator_graph",
    "build_simple_orchestrator_flow",
    
    # Legacy state
    "OrchestratorState",
]
