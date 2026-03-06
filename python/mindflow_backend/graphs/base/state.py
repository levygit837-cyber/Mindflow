"""Graph state management for MindFlow graphs."""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class GraphState(TypedDict, total=False):
    """Base state structure for all graphs."""
    
    # Core execution state
    session_id: str
    graph_id: str
    current_node: str
    execution_id: str
    
    # Message and context
    message: str
    provider: str
    model: str
    
    # Results and errors
    response: str
    error: Optional[str]
    
    # Metadata
    start_time: float
    end_time: float
    metrics: Dict[str, Any]
    
    # Custom state per graph type
    custom_state: Dict[str, Any]


class StateManager:
    """Manages state persistence and retrieval for graphs."""
    
    def __init__(self) -> None:
        self._states: Dict[str, GraphState] = {}
        self._execution_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_state(
        self, 
        session_id: str,
        graph_id: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> GraphState:
        """Create a new graph state."""
        execution_id = str(uuid4())
        
        state: GraphState = {
            "session_id": session_id,
            "graph_id": graph_id,
            "current_node": "",
            "execution_id": execution_id,
            "message": "",
            "provider": "",
            "model": "",
            "response": "",
            "error": None,
            "start_time": 0.0,
            "end_time": 0.0,
            "metrics": {},
            "custom_state": {},
        }
        
        if initial_data:
            state.update(initial_data)
        
        self._states[execution_id] = state
        self._execution_history[execution_id] = []
        
        return state
    
    def get_state(self, execution_id: str) -> Optional[GraphState]:
        """Retrieve state by execution ID."""
        return self._states.get(execution_id)
    
    def update_state(
        self, 
        execution_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[GraphState]:
        """Update state with new values."""
        if execution_id not in self._states:
            return None
        
        state = self._states[execution_id]
        state.update(updates)
        
        # Track history for debugging
        self._execution_history[execution_id].append({
            "timestamp": state.get("start_time", 0),
            "node": state.get("current_node"),
            "updates": list(updates.keys()),
        })
        
        return state
    
    def delete_state(self, execution_id: str) -> bool:
        """Delete state from memory."""
        if execution_id in self._states:
            del self._states[execution_id]
            if execution_id in self._execution_history:
                del self._execution_history[execution_id]
            return True
        return False
    
    def get_execution_history(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get execution history for debugging."""
        return self._execution_history.get(execution_id, [])
    
    def list_active_states(self) -> List[str]:
        """List all active execution IDs."""
        return list(self._states.keys())


class StateSnapshot(BaseModel):
    """Serializable snapshot of graph state."""
    
    execution_id: str
    session_id: str
    graph_id: str
    current_node: str
    state_data: Dict[str, Any]
    timestamp: float
    checksum: str
    
    @classmethod
    def from_state(cls, state: GraphState) -> StateSnapshot:
        """Create snapshot from graph state."""
        import hashlib
        import json
        
        state_data = dict(state)
        state_json = json.dumps(state_data, sort_keys=True)
        checksum = hashlib.md5(state_json.encode()).hexdigest()
        
        return cls(
            execution_id=state["execution_id"],
            session_id=state["session_id"],
            graph_id=state["graph_id"],
            current_node=state["current_node"],
            state_data=state_data,
            timestamp=state.get("start_time", 0),
            checksum=checksum,
        )
