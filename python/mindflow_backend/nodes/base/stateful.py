"""Stateful node mixin for persistent node behavior."""

from __future__ import annotations

from typing import Any

from mindflow_backend.nodes.base.node import BaseNode


class StatefulNode:
    """Mixin for nodes that maintain state between executions."""
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._node_state: dict[str, Any] = {}
        self._state_persistence_enabled = True
        self._state_key_prefix = f"node_state_{self.node_id}"
    
    def get_node_state(self, key: str, default: Any = None) -> Any:
        """Get a value from the node's state."""
        return self._node_state.get(key, default)
    
    def set_node_state(self, key: str, value: Any) -> None:
        """Set a value in the node's state."""
        self._node_state[key] = value
    
    def update_node_state(self, updates: dict[str, Any]) -> None:
        """Update multiple values in the node's state."""
        self._node_state.update(updates)
    
    def clear_node_state(self) -> None:
        """Clear all node state."""
        self._node_state.clear()
    
    def get_all_node_state(self) -> dict[str, Any]:
        """Get a copy of all node state."""
        return dict(self._node_state)
    
    def enable_state_persistence(self, enabled: bool = True) -> None:
        """Enable or disable state persistence."""
        self._state_persistence_enabled = enabled
    
    def is_state_persistence_enabled(self) -> bool:
        """Check if state persistence is enabled."""
        return self._state_persistence_enabled
    
    async def save_state_to_context(self, state: dict[str, Any]) -> None:
        """Save node state to the execution context."""
        if not self._state_persistence_enabled:
            return
        
        if "node_states" not in state:
            state["node_states"] = {}
        
        state["node_states"][self.node_id] = dict(self._node_state)
    
    async def load_state_from_context(self, state: dict[str, Any]) -> None:
        """Load node state from the execution context."""
        if not self._state_persistence_enabled:
            return
        
        node_states = state.get("node_states", {})
        if self.node_id in node_states:
            self._node_state = dict(node_states[self.node_id])
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute with automatic state management."""
        # Load state before execution
        await self.load_state_from_context(state)
        
        try:
            # Execute the actual node logic
            result = await super().execute(state)
            
            # Save state after execution
            await self.save_state_to_context(result)
            
            return result
            
        except Exception:
            # Even on error, save state
            await self.save_state_to_context(state)
            raise
    
    def get_state_info(self) -> dict[str, Any]:
        """Get information about the node's state."""
        return {
            "node_id": self.node_id,
            "state_keys": list(self._node_state.keys()),
            "state_size": len(str(self._node_state)),
            "persistence_enabled": self._state_persistence_enabled,
        }


class CounterStatefulNode(StatefulNode, BaseNode):
    """Example stateful node that maintains a counter."""
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.set_node_state("execution_count", 0)
        self.set_node_state("total_execution_time", 0.0)
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute with counter tracking."""
        import time
        
        start_time = time.time()
        
        # Increment execution count
        count = self.get_node_state("execution_count", 0) + 1
        self.set_node_state("execution_count", count)
        
        try:
            # Execute the actual logic
            result = await super().execute(state)
            
            # Update total execution time
            execution_time = time.time() - start_time
            total_time = self.get_node_state("total_execution_time", 0.0) + execution_time
            self.set_node_state("total_execution_time", total_time)
            
            # Add metrics to result
            result["node_metrics"] = {
                "execution_count": count,
                "execution_time": execution_time,
                "total_execution_time": total_time,
                "average_execution_time": total_time / count if count > 0 else 0.0,
            }
            
            return result
            
        except Exception:
            # Still update execution time on error
            execution_time = time.time() - start_time
            total_time = self.get_node_state("total_execution_time", 0.0) + execution_time
            self.set_node_state("total_execution_time", total_time)
            
            raise
    
    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate inputs for counter stateful node."""
        return []  # No specific validation required
