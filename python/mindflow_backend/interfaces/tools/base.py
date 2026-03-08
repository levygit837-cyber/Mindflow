"""Base tool interfaces for MindFlow backend.

Defines the contract that all tools must implement to ensure
consistent behavior, validation, and integration with the
enhanced tool registry system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from mindflow_backend.schemas.orchestration.orchestrator import AgentType


class ToolInterface(ABC):
    """Abstract base interface for all agent tools.
    
    All tools must implement this interface to ensure consistent
    behavior, validation, and integration capabilities.
    """
    
    def __init__(self):
        """Initialize tool with default configuration."""
        self.name = self.__class__.__name__.replace("Tool", "").lower()
        self.description = self.__doc__ or "No description available"
        self._capabilities: Optional[Dict[str, Any]] = None
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters.
        
        Args:
            *args: Positional arguments (deprecated, use kwargs)
            **kwargs: Named parameters for tool execution
            
        Returns:
            Dictionary containing tool execution result with standardized format:
            {
                "success": bool,
                "result": Any,
                "error": Optional[str],
                "metadata": Optional[Dict[str, Any]]
            }
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the tool schema for validation and documentation.
        
        Returns:
            Dictionary containing:
            {
                "name": str,
                "description": str,
                "parameters": Dict[str, Any],
                "returns": Dict[str, Any]
            }
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return tool capabilities and requirements.
        
        Returns:
            Dictionary describing:
            {
                "requires_backend": bool,
                "requires_sandbox": bool,
                "supported_agents": List[AgentType],
                "async_execution": bool,
                "resource_requirements": Dict[str, Any]
            }
        """
        if self._capabilities is None:
            self._capabilities = {
                "requires_backend": False,
                "requires_sandbox": False,
                "supported_agents": list(AgentType),
                "async_execution": True,
                "resource_requirements": {}
            }
        return self._capabilities
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate input parameters before execution.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        schema = self.get_schema()
        required_params = schema.get("parameters", {}).get("required", [])
        
        # Check required parameters
        for param in required_params:
            if param not in parameters:
                return False, f"Missing required parameter: {param}"
        
        # Basic type validation (can be extended with Pydantic)
        param_schemas = schema.get("parameters", {}).get("properties", {})
        for param_name, param_value in parameters.items():
            if param_name in param_schemas:
                param_schema = param_schemas[param_name]
                expected_type = param_schema.get("type")
                
                if expected_type == "string" and not isinstance(param_value, str):
                    return False, f"Parameter {param_name} must be a string"
                elif expected_type == "integer" and not isinstance(param_value, int):
                    return False, f"Parameter {param_name} must be an integer"
                elif expected_type == "boolean" and not isinstance(param_value, bool):
                    return False, f"Parameter {param_name} must be a boolean"
                elif expected_type == "array" and not isinstance(param_value, list):
                    return False, f"Parameter {param_name} must be a list"
        
        return True, None
    
    def is_available_for_agent(self, agent_type: AgentType) -> bool:
        """Check if tool is available for specific agent type.
        
        Args:
            agent_type: Agent type to check availability for
            
        Returns:
            True if tool can be used by this agent type
        """
        capabilities = self.get_capabilities()
        supported_agents = capabilities.get("supported_agents", list(AgentType))
        return agent_type in supported_agents
    
    def get_execution_context(self, **kwargs) -> Dict[str, Any]:
        """Prepare execution context for tool.
        
        Args:
            **kwargs: Execution parameters
            
        Returns:
            Context dictionary for tool execution
        """
        return {
            "tool_name": self.name,
            "parameters": kwargs,
            "timestamp": self._get_timestamp(),
            "capabilities": self.get_capabilities()
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for logging."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _format_result(
        self, 
        success: bool, 
        result: Any = None, 
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format standardized tool result.
        
        Args:
            success: Whether execution was successful
            result: Main result data
            error: Error message if execution failed
            metadata: Additional metadata
            
        Returns:
            Standardized result dictionary
        """
        return {
            "success": success,
            "result": result,
            "error": error,
            "metadata": metadata or {},
            "tool_name": self.name,
            "timestamp": self._get_timestamp()
        }


class AsyncToolInterface(ToolInterface):
    """Base class for tools that require async execution.
    
    Extends ToolInterface with async-specific utilities and
    context management for concurrent execution.
    """
    
    async def execute_async(self, *args, **kwargs) -> Dict[str, Any]:
        """Async wrapper for execute method.
        
        Provides consistent async interface and error handling.
        """
        try:
            # Validate parameters
            is_valid, error_msg = self.validate_parameters(kwargs)
            if not is_valid:
                return self._format_result(
                    success=False, 
                    error=f"Parameter validation failed: {error_msg}"
                )
            
            # Prepare context
            context = self.get_execution_context(**kwargs)
            
            # Execute tool
            result = await self.execute(*args, **kwargs)
            
            # Ensure result is properly formatted
            if isinstance(result, dict) and "success" in result:
                return result
            else:
                return self._format_result(success=True, result=result)
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )


class StatefulToolInterface(AsyncToolInterface):
    """Base class for tools that maintain state between executions.
    
    Provides state management capabilities for tools that need
    to maintain context across multiple calls.
    """
    
    def __init__(self):
        super().__init__()
        self._state: Dict[str, Any] = {}
        self._state_ttl: Optional[int] = None  # Time-to-live in seconds
    
    def set_state(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set state value with optional TTL.
        
        Args:
            key: State key
            value: State value
            ttl: Time-to-live in seconds
        """
        import time
        
        self._state[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl or self._state_ttl
        }
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value if not expired.
        
        Args:
            key: State key
            default: Default value if key doesn't exist or is expired
            
        Returns:
            State value or default
        """
        import time
        
        if key not in self._state:
            return default
            
        state_entry = self._state[key]
        ttl = state_entry.get("ttl")
        
        if ttl is not None:
            age = time.time() - state_entry["timestamp"]
            if age > ttl:
                del self._state[key]
                return default
                
        return state_entry["value"]
    
    def clear_state(self, key: Optional[str] = None) -> None:
        """Clear state entries.
        
        Args:
            key: Specific key to clear, or None to clear all
        """
        if key is None:
            self._state.clear()
        elif key in self._state:
            del self._state[key]


# Tool schema and permission classes
class ToolSchema(BaseModel):
    """Schema definition for tool parameters and returns."""
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any]
    examples: Optional[List[Dict[str, Any]]] = None


class ToolPermission(BaseModel):
    """Permission definition for tool access control."""
    required_level: str
    allowed_agents: List[str]
    resource_requirements: Dict[str, Any]
    security_constraints: Optional[Dict[str, Any]] = None
