"""Respond node - finalizes the response and handles post-processing."""

from __future__ import annotations

from typing import Any, Dict

from omnimind_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from omnimind_backend.nodes.base.stateful import StatefulNode


class RespondNode(StatefulNode, BaseNode):
    """Node that finalizes the response and handles post-processing."""
    
    def __init__(self, node_id: str = "respond") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.FORMATTER,
            category=NodeCategory.DATA_PROCESSING,
            description="Finalize the response and handle post-processing"
        )
        
        # This node typically doesn't require specific inputs
        # as it's a pass-through node in the current implementation
        self.config.outputs = {"response", "error", "final_response"}
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute response finalization (currently a pass-through)."""
        from omnimind_backend.infra.logging import get_logger
        
        _logger = get_logger(__name__)
        
        # Update node state
        self.set_node_state("response_count", self.get_node_state("response_count", 0) + 1)
        self.set_node_state("last_response_time", self._get_timestamp())
        
        # Store the response for potential post-processing
        response = state.get("response", "")
        error = state.get("error")
        
        # In the current implementation, this is a pass-through
        # but we can add post-processing logic here
        
        if error:
            _logger.warning("respond_node_error", error=error)
            self.set_node_state("error_count", self.get_node_state("error_count", 0) + 1)
        
        # Add any final formatting or enrichment
        final_response = self._format_response(response, error)
        
        return {
            "response": response,
            "error": error,
            "final_response": final_response,
        }
    
    def _format_response(self, response: str, error: str | None) -> str:
        """Format the final response."""
        if error:
            return f"Error occurred: {error}\nPartial response: {response}"
        
        # Add any response formatting here
        # For example, adding timestamps, formatting, etc.
        if response:
            return response
        
        return "No response generated."
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def validate_inputs(self, state: Dict[str, Any]) -> list[str]:
        """Validate respond node inputs."""
        # This node is flexible and doesn't require specific inputs
        # as it handles various states gracefully
        return []
    
    async def _on_initialize(self) -> None:
        """Initialize the respond node."""
        self.set_node_state("response_count", 0)
        self.set_node_state("error_count", 0)
        self.set_node_state("last_response_time", 0.0)
