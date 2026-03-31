"""Respond node - finalizes the response and handles post-processing."""

from __future__ import annotations

from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.nodes.base.stateful import StatefulNode


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
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute response finalization with memory storage."""
        from mindflow_backend.infra.logging import get_logger
        
        _logger = get_logger(__name__)
        
        # Update node state
        self.set_node_state("response_count", self.get_node_state("response_count", 0) + 1)
        self.set_node_state("last_response_time", self._get_timestamp())
        
        # Store the response for potential post-processing
        response = state.get("response", "")
        error = state.get("error")
        
        # Store interaction in memory
        try:
            session_id = state.get("session_id", "")
            message = state.get("message", "")
            decision = state.get("decision")
            
            if session_id and message and response:
                from mindflow_backend.orchestrator.memory_integration import (
                    store_orchestrator_interaction,
                )
                
                # Calculate token positions (simplified)
                message_tokens = len(message.split())
                response_tokens = len(response.split())
                
                # Get agent ID from decision
                agent_id = "unknown"
                if decision and hasattr(decision, 'agent'):
                    agent_id = decision.agent.value
                
                # Store interaction
                message_id, response_id = await store_orchestrator_interaction(
                    session_id=session_id,
                    agent_id=agent_id,
                    message=message,
                    response=response,
                    token_start=0,  # Simplified token tracking
                    token_end=message_tokens + response_tokens,
                )
                
                _logger.debug(f"Stored interaction: message_id={message_id}, response_id={response_id}")
                
        except Exception as e:
            _logger.error(f"Failed to store interaction in memory: {e}")
        
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
    
    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate respond node inputs."""
        # This node is flexible and doesn't require specific inputs
        # as it handles various states gracefully
        return []
    
    async def _on_initialize(self) -> None:
        """Initialize the respond node."""
        self.set_node_state("response_count", 0)
        self.set_node_state("error_count", 0)
        self.set_node_state("last_response_time", 0.0)
