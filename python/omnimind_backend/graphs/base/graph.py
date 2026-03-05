"""Base graph classes for OmniMind orchestration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from omnimind_backend.graphs.base.state import GraphState, StateManager
from omnimind_backend.graphs.base.types import GraphConfig, GraphMetrics, GraphType, NodeConnection


class BaseGraph(ABC):
    """Abstract base class for all graphs in OmniMind."""
    
    def __init__(
        self,
        graph_id: str,
        config: Optional[GraphConfig] = None,
        state_manager: Optional[StateManager] = None
    ) -> None:
        self.graph_id = graph_id
        self.config = config or GraphConfig()
        self.state_manager = state_manager or StateManager()
        self._nodes: Dict[str, Any] = {}
        self._connections: List[NodeConnection] = []
        self._entry_point: str = ""
    
    @property
    @abstractmethod
    def graph_type(self) -> GraphType:
        """Return the type of this graph."""
        ...
    
    @abstractmethod
    async def execute(self, state: GraphState) -> GraphState:
        """Execute the graph with the given state."""
        ...
    
    @abstractmethod
    def validate(self) -> List[str]:
        """Validate the graph structure and return any issues."""
        ...
    
    def add_node(self, node_id: str, node: Any) -> None:
        """Add a node to the graph."""
        if node_id in self._nodes:
            raise ValueError(f"Node {node_id} already exists in graph")
        self._nodes[node_id] = node
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the graph."""
        if node_id in self._nodes:
            del self._nodes[node_id]
            # Remove connections involving this node
            self._connections = [
                conn for conn in self._connections
                if conn.source_node != node_id and conn.target_node != node_id
            ]
            return True
        return False
    
    def add_connection(self, connection: NodeConnection) -> None:
        """Add a connection between nodes."""
        if connection.source_node not in self._nodes:
            raise ValueError(f"Source node {connection.source_node} not found")
        if connection.target_node not in self._nodes:
            raise ValueError(f"Target node {connection.target_node} not found")
        
        self._connections.append(connection)
    
    def set_entry_point(self, node_id: str) -> None:
        """Set the entry point node for the graph."""
        if node_id not in self._nodes:
            raise ValueError(f"Entry point node {node_id} not found")
        self._entry_point = node_id
    
    def get_node(self, node_id: str) -> Optional[Any]:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def get_nodes(self) -> Dict[str, Any]:
        """Get all nodes in the graph."""
        return dict(self._nodes)
    
    def get_connections(self) -> List[NodeConnection]:
        """Get all connections in the graph."""
        return list(self._connections)
    
    def get_next_nodes(self, current_node: str) -> List[str]:
        """Get the next nodes based on connections."""
        return [
            conn.target_node 
            for conn in self._connections 
            if conn.source_node == current_node
        ]
    
    def create_state(
        self, 
        session_id: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> GraphState:
        """Create a new state for this graph."""
        return self.state_manager.create_state(
            session_id=session_id,
            graph_id=self.graph_id,
            initial_data=initial_data
        )
    
    async def execute_with_metrics(
        self, 
        state: GraphState
    ) -> tuple[GraphState, GraphMetrics]:
        """Execute the graph and collect metrics."""
        import time
        
        start_time = time.time()
        state["start_time"] = start_time
        
        nodes_executed = 0
        nodes_failed = 0
        total_tokens_used = 0
        error_details = []
        
        try:
            result_state = await self.execute(state)
            
            # Extract metrics from state if available
            metrics = result_state.get("metrics", {})
            nodes_executed = metrics.get("nodes_executed", 0)
            nodes_failed = metrics.get("nodes_failed", 0)
            total_tokens_used = metrics.get("total_tokens_used", 0)
            error_details = metrics.get("error_details", [])
            
        except Exception as e:
            error_details.append(str(e))
            nodes_failed += 1
            result_state = state
            result_state["error"] = str(e)
        
        end_time = time.time()
        result_state["end_time"] = end_time
        
        metrics = GraphMetrics(
            execution_time=end_time - start_time,
            nodes_executed=nodes_executed,
            nodes_failed=nodes_failed,
            total_tokens_used=total_tokens_used,
            error_details=error_details,
        )
        
        return result_state, metrics
    
    def validate_structure(self) -> List[str]:
        """Validate the basic structure of the graph."""
        issues = []
        
        if not self._nodes:
            issues.append("Graph has no nodes")
        
        if not self._entry_point:
            issues.append("Graph has no entry point")
        elif self._entry_point not in self._nodes:
            issues.append(f"Entry point {self._entry_point} not found in nodes")
        
        # Check for orphaned nodes (no incoming connections except entry point)
        connected_nodes = {self._entry_point}
        for conn in self._connections:
            connected_nodes.add(conn.source_node)
            connected_nodes.add(conn.target_node)
        
        orphaned_nodes = set(self._nodes.keys()) - connected_nodes
        if orphaned_nodes:
            issues.append(f"Orphaned nodes: {', '.join(orphaned_nodes)}")
        
        # Check for connections to non-existent nodes
        for conn in self._connections:
            if conn.source_node not in self._nodes:
                issues.append(f"Connection references non-existent source: {conn.source_node}")
            if conn.target_node not in self._nodes:
                issues.append(f"Connection references non-existent target: {conn.target_node}")
        
        return issues
    
    def get_graph_info(self) -> Dict[str, Any]:
        """Get information about the graph structure."""
        return {
            "graph_id": self.graph_id,
            "graph_type": self.graph_type.value,
            "node_count": len(self._nodes),
            "connection_count": len(self._connections),
            "entry_point": self._entry_point,
            "nodes": list(self._nodes.keys()),
            "config": self.config.dict(),
        }


class SimpleGraph(BaseGraph):
    """Simple linear graph implementation."""
    
    @property
    def graph_type(self) -> GraphType:
        return GraphType.SIMPLE
    
    async def execute(self, state: GraphState) -> GraphState:
        """Execute nodes in linear sequence."""
        current_node = self._entry_point
        
        nodes_executed = 0
        nodes_failed = 0
        
        while current_node:
            state["current_node"] = current_node
            
            try:
                node = self._nodes[current_node]
                if hasattr(node, 'execute'):
                    result = await node.execute(state)
                    if isinstance(result, dict):
                        state.update(result)
                else:
                    # Assume it's a callable function
                    result = await node(state)
                    if isinstance(result, dict):
                        state.update(result)
                
                nodes_executed += 1
                
            except Exception as e:
                nodes_failed += 1
                state["error"] = str(e)
                break
            
            # Get next node (simple linear execution)
            next_nodes = self.get_next_nodes(current_node)
            current_node = next_nodes[0] if next_nodes else None
        
        # Update metrics
        state["metrics"] = {
            "nodes_executed": nodes_executed,
            "nodes_failed": nodes_failed,
            "total_tokens_used": 0,  # Would be populated by nodes
            "error_details": [state["error"]] if state.get("error") else [],
        }
        
        return state
    
    def validate(self) -> List[str]:
        """Validate simple graph structure."""
        issues = self.validate_structure()
        
        # Simple graph should have exactly one path
        if len(self._connections) != len(self._nodes) - 1:
            issues.append("Simple graph should have exactly one connection per node (except last)")
        
        return issues
