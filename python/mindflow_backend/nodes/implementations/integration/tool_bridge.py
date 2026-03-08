"""Tool Bridge Node - Integrates Nodes with Tools system.

This node provides a clean interface between the Nodes system and the Tools system,
isolating dependencies and maintaining separation of concerns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode


class ToolBridge(StatefulNode, BaseNode):
    """Bridge node for integrating with Tools system.
    
    This node isolates the dependency on the Tools system, providing
    a clean interface for tool execution while maintaining architectural
    separation between Nodes and Tools.
    """
    
    def __init__(
        self,
        node_id: str = "tool_bridge",
        allowed_tools: Optional[List[str]] = None,
        tool_timeout: float = 30.0
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.PROCESSING,
            category=NodeCategory.INTEGRATION,
            description="Bridge node for tool system integration"
        )
        
        self.allowed_tools = allowed_tools or []
        self.tool_timeout = tool_timeout
        
        # Required inputs
        self.config.required_inputs = {"tool_name", "tool_args"}
        self.config.outputs = {"result", "error", "metadata"}
        
        # Internal state for tool integration
        self._tools_registry = None
        self._available_tools = {}
    
    async def initialize(self) -> None:
        """Initialize the tool bridge and its dependencies."""
        await super().initialize()
        
        # Import tool dependencies only when needed
        from mindflow_backend.agents.tools import create_default_registry
        from mindflow_backend.infra.logging import get_logger
        
        self._logger = get_logger(__name__)
        
        try:
            # Create tools registry
            self._tools_registry = create_default_registry()
            
            # Get available tools
            self._available_tools = {
                name: tool_class 
                for name, tool_class in self._tools_registry.get_all_tools().items()
                if not self.allowed_tools or name in self.allowed_tools
            }
            
            self._logger.info("tool_bridge_initialized", 
                           available_tools=list(self._available_tools.keys()),
                           allowed_tools=self.allowed_tools)
            
        except Exception as e:
            self._logger.error("tool_bridge_initialization_failed", error=str(e))
            raise
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool logic through the bridge interface."""
        if not self._tools_registry:
            raise RuntimeError("Tool bridge not properly initialized")
        
        try:
            tool_name = state["tool_name"]
            tool_args = state.get("tool_args", {})
            
            # Validate tool availability
            if tool_name not in self._available_tools:
                available_tools = list(self._available_tools.keys())
                raise ValueError(f"Tool '{tool_name}' not available. Available tools: {available_tools}")
            
            # Get tool class and instantiate
            tool_class = self._available_tools[tool_name]
            tool_instance = tool_class()
            
            # Execute tool with timeout
            import asyncio
            result = await asyncio.wait_for(
                self._execute_tool_safely(tool_instance, tool_args),
                timeout=self.tool_timeout
            )
            
            return {
                "result": result["output"],
                "metadata": {
                    "tool_name": tool_name,
                    "execution_time": result.get("execution_time", 0),
                    "success": result.get("success", True),
                    "tool_version": getattr(tool_instance, 'version', '1.0.0'),
                },
                "error": None
            }
            
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after {self.tool_timeout}s"
            self._logger.error("tool_bridge_timeout", tool=tool_name, timeout=self.tool_timeout)
            
            return {
                "result": None,
                "metadata": {"timeout": True, "tool_name": tool_name},
                "error": error_msg
            }
            
        except Exception as e:
            self._logger.error("tool_bridge_execution_failed", 
                           tool=state.get("tool_name"), 
                           error=str(e))
            
            return {
                "result": None,
                "metadata": {"error_type": type(e).__name__},
                "error": str(e)
            }
    
    async def _execute_tool_safely(self, tool_instance: Any, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with error handling and timing."""
        import time
        
        start_time = time.time()
        
        try:
            # Validate tool arguments
            if hasattr(tool_instance, 'validate_args'):
                validation_result = tool_instance.validate_args(tool_args)
                if not validation_result.is_valid:
                    raise ValueError(f"Invalid tool arguments: {validation_result.errors}")
            
            # Execute tool
            if asyncio.iscoroutinefunction(tool_instance.execute):
                output = await tool_instance.execute(**tool_args)
            else:
                output = tool_instance.execute(**tool_args)
            
            execution_time = time.time() - start_time
            
            return {
                "output": output,
                "execution_time": execution_time,
                "success": True
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return {
                "output": None,
                "execution_time": execution_time,
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available tools with their metadata."""
        if not self._available_tools:
            return {}
        
        tools_info = {}
        for name, tool_class in self._available_tools.items():
            try:
                # Try to get tool metadata without instantiating
                metadata = {
                    "name": name,
                    "description": getattr(tool_class, 'description', 'No description available'),
                    "category": getattr(tool_class, 'category', 'general'),
                    "version": getattr(tool_class, 'version', '1.0.0'),
                    "parameters": getattr(tool_class, 'parameters', {}),
                }
                tools_info[name] = metadata
            except Exception as e:
                # Tool metadata unavailable, but still list the tool
                tools_info[name] = {
                    "name": name,
                    "description": "Metadata unavailable",
                    "error": str(e)
                }
        
        return tools_info
    
    def validate_tool_args(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool arguments without executing."""
        if tool_name not in self._available_tools:
            return {
                "valid": False,
                "error": f"Tool '{tool_name}' not available"
            }
        
        try:
            tool_class = self._available_tools[tool_name]
            tool_instance = tool_class()
            
            if hasattr(tool_instance, 'validate_args'):
                validation_result = tool_instance.validate_args(tool_args)
                return {
                    "valid": validation_result.is_valid,
                    "errors": getattr(validation_result, 'errors', []),
                    "warnings": getattr(validation_result, 'warnings', [])
                }
            else:
                # Tool doesn't have validation
                return {"valid": True, "errors": [], "warnings": []}
                
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    async def cleanup(self) -> None:
        """Cleanup tool bridge resources."""
        self._tools_registry = None
        self._available_tools = {}
        
        await super().cleanup()
    
    def update_allowed_tools(self, allowed_tools: List[str]) -> None:
        """Dynamically update the list of allowed tools."""
        self.allowed_tools = allowed_tools
        
        # Reinitialize available tools
        if self._tools_registry:
            self._available_tools = {
                name: tool_class 
                for name, tool_class in self._tools_registry.get_all_tools().items()
                if not self.allowed_tools or name in self.allowed_tools
            }
