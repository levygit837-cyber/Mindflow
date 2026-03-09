"""Response node with automatic memory storage.

Handles response formatting and automatic storage of
interactions in the memory service.
"""

from __future__ import annotations

from typing import Any, Dict
import asyncio

from mindflow_backend.infra.logging import get_logger
from .memory_integration import store_orchestrator_interaction

_logger = get_logger(__name__)


async def response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format response and store interaction in memory.
    
    Args:
        state: Orchestrator state with response.
        
    Returns:
        Updated state with stored interaction IDs.
    """
    response = state.get("response", "")
    error = state.get("error")
    session_id = state.get("session_id", "")
    message = state.get("message", "")
    decision = state.get("decision")
    
    # Store interaction in memory
    try:
        if session_id and message and response:
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
            
            return {
                "response": response,
                "error": error,
                "message_id": message_id,
                "response_id": response_id,
                "stored": True,
            }
        else:
            _logger.warning("Skipping memory storage - missing required fields")
            return {"response": response, "error": error, "stored": False}
            
    except Exception as e:
        _logger.error(f"Failed to store interaction in memory: {e}")
        return {"response": response, "error": error, "stored": False}
