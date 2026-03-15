"""Graph orchestration for MindFlow."""

# Base classes
from mindflow_backend.graphs.base import (
    BaseGraph,
    GraphType,
    GraphState,
    StateManager,
    GraphConfig,
    NodeConnection,
)

# Workflow graphs
from mindflow_backend.graphs.implementations.workflow import (
    SequentialWorkflowGraph,
    ParallelWorkflowGraph,
    ConditionalWorkflowGraph,
)

# Orchestrator implementations
from mindflow_backend.graphs.implementations.orchestrator import (
    SimpleOrchestratorGraph,
    MultiAgentGraph,
    DecompositionGraph,
)

# Factory
from mindflow_backend.graphs.factory import (
    GraphFactory,
    get_graph_factory,
    create_orchestrator_graph,
    build_simple_orchestrator_flow,
)

# Backward compatibility
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import (
    SimpleOrchestratorGraph,
    build_simple_orchestrator_flow,
)
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import OrchestratorState

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
