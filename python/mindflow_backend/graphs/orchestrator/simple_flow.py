"""Simple orchestrator graph - route → execute → respond flow.

This is the current Phase 2 implementation migrated to the new architecture.
"""

from __future__ import annotations

from typing import Any, Dict

from mindflow_backend.graphs.base.graph import SimpleGraph
from mindflow_backend.graphs.base.types import GraphConfig, GraphType
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.nodes.orchestrator.route_node import RouteNode
from mindflow_backend.nodes.orchestrator.execute_node import ExecuteNode
from mindflow_backend.nodes.orchestrator.respond_node import RespondNode


class SimpleOrchestratorGraph(SimpleGraph):
    """Simple orchestrator graph with linear flow: route → execute → respond."""
    
    def __init__(self, graph_id: str = "simple_orchestrator") -> None:
        config = GraphConfig(
            graph_type=GraphType.SIMPLE,
            enable_streaming=True,
            timeout_per_node=30.0,
        )
        
        super().__init__(graph_id, config)
        
        # Create nodes
        self.route_node = RouteNode("route")
        self.execute_node = ExecuteNode("execute")
        self.respond_node = RespondNode("respond")
        
        # Add nodes to graph
        self.add_node("route", self.route_node)
        self.add_node("execute", self.execute_node)
        self.add_node("respond", self.respond_node)
        
        # Set up connections
        self._setup_connections()
        
        # Set entry point
        self.set_entry_point("route")
    
    def _setup_connections(self) -> None:
        """Set up the linear connections between nodes."""
        from mindflow_backend.graphs.base.types import NodeConnection
        
        self.add_connection(NodeConnection(
            source_node="route",
            target_node="execute"
        ))
        
        self.add_connection(NodeConnection(
            source_node="execute", 
            target_node="respond"
        ))
    
    @property
    def graph_type(self) -> GraphType:
        return GraphType.SIMPLE
    
    async def execute(self, state: GraphState) -> GraphState:
        """Execute the simple orchestrator flow."""
        # Initialize nodes
        await self.route_node.initialize()
        await self.execute_node.initialize()
        await self.respond_node.initialize()
        
        # Execute using parent class logic
        return await super().execute(state)
    
    def validate(self) -> list[str]:
        """Validate the simple orchestrator graph."""
        issues = super().validate()
        
        # Check that all required nodes are present
        required_nodes = ["route", "execute", "respond"]
        for node_id in required_nodes:
            if node_id not in self._nodes:
                issues.append(f"Missing required node: {node_id}")
        
        # Validate flow is linear
        if len(self._connections) != 2:
            issues.append("Simple orchestrator should have exactly 2 connections")
        
        return issues


# Backward compatibility function
def build_simple_orchestrator_flow() -> Any:
    """Build a simple orchestrator flow with backward compatibility.
    
    Returns a function that mimics the original interface.
    """
    graph = SimpleOrchestratorGraph()
    
    async def simple_orchestrate(state: dict[str, Any]) -> dict[str, Any]:
        """Simple orchestration using the new graph architecture."""
        # Create graph state if needed
        if "execution_id" not in state:
            graph_state = graph.create_state(
                session_id=state.get("session_id", "unknown"),
                initial_data=state
            )
        else:
            graph_state = state
        
        # Execute the graph
        result_state = await graph.execute(graph_state)
        
        return result_state
    
    return simple_orchestrate
