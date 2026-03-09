"""
MCP Tool Handlers

Handlers for processing MCP tool-related operations including
tool discovery, execution, and result management.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

from mindflow_backend.schemas.mcp.tools import (
    MCPToolDefinition, MCPToolResult, MCPToolCall, MCPToolParameter
)
from mindflow_backend.interfaces.mcp.handlers.message import RequestHandler


class ToolExecutor:
    """
    Base class for tool executors.
    
    Tool executors are responsible for actually running tools
    with provided arguments and returning results.
    """
    
    def __init__(self):
        """Initialize the tool executor."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """
        Execute a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool execution arguments
            
        Returns:
            MCPToolResult: Execution result
        """
        try:
            # Get tool implementation
            tool_func = getattr(self, f"execute_{tool_name}", None)
            if not tool_func:
                return MCPToolResult.error_result(
                    error=f"Tool '{tool_name}' not found",
                    error_code="TOOL_NOT_FOUND"
                )
            
            # Validate arguments
            validation_result = await self.validate_arguments(tool_name, arguments)
            if not validation_result.success:
                return validation_result
            
            # Execute the tool
            start_time = asyncio.get_event_loop().time()
            result = await tool_func(**arguments)
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return MCPToolResult.success_result(
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Error executing tool '{tool_name}': {e}")
            return MCPToolResult.error_result(
                error=str(e),
                error_code="EXECUTION_ERROR"
            )
    
    async def validate_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """
        Validate tool arguments against tool definition.
        
        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate
            
        Returns:
            MCPToolResult: Validation result
        """
        try:
            # Get tool definition
            tool_def = await self.get_tool_definition(tool_name)
            if not tool_def:
                return MCPToolResult.error_result(
                    error=f"Tool definition for '{tool_name}' not found",
                    error_code="TOOL_DEFINITION_NOT_FOUND"
                )
            
            # Check required parameters
            required_params = tool_def.input_schema.required
            for param in required_params:
                if param not in arguments:
                    return MCPToolResult.error_result(
                        error=f"Required parameter '{param}' missing",
                        error_code="MISSING_PARAMETER"
                    )
            
            # Validate parameter types and constraints
            for param_name, param_value in arguments.items():
                if param_name in tool_def.input_schema.properties:
                    param_def = tool_def.input_schema.properties[param_name]
                    validation_result = self.validate_parameter(param_def, param_value)
                    if not validation_result.success:
                        return validation_result
            
            return MCPToolResult.success_result(True)
            
        except Exception as e:
            return MCPToolResult.error_result(
                error=f"Validation error: {e}",
                error_code="VALIDATION_ERROR"
            )
    
    def validate_parameter(self, param_def: MCPToolParameter, value: Any) -> MCPToolResult:
        """
        Validate a single parameter value.
        
        Args:
            param_def: Parameter definition
            value: Value to validate
            
        Returns:
            MCPToolResult: Validation result
        """
        # Type validation
        if param_def.type.value == "string" and not isinstance(value, str):
            return MCPToolResult.error_result(
                error=f"Parameter '{param_def.name}' must be a string",
                error_code="TYPE_MISMATCH"
            )
        elif param_def.type.value == "integer" and not isinstance(value, int):
            return MCPToolResult.error_result(
                error=f"Parameter '{param_def.name}' must be an integer",
                error_code="TYPE_MISMATCH"
            )
        elif param_def.type.value == "number" and not isinstance(value, (int, float)):
            return MCPToolResult.error_result(
                error=f"Parameter '{param_def.name}' must be a number",
                error_code="TYPE_MISMATCH"
            )
        elif param_def.type.value == "boolean" and not isinstance(value, bool):
            return MCPToolResult.error_result(
                error=f"Parameter '{param_def.name}' must be a boolean",
                error_code="TYPE_MISMATCH"
            )
        
        # Enum validation
        if param_def.enum and value not in param_def.enum:
            return MCPToolResult.error_result(
                error=f"Parameter '{param_def.name}' must be one of {param_def.enum}",
                error_code="INVALID_ENUM_VALUE"
            )
        
        # String constraints
        if isinstance(value, str):
            if param_def.min_length and len(value) < param_def.min_length:
                return MCPToolResult.error_result(
                    error=f"Parameter '{param_def.name}' must be at least {param_def.min_length} characters",
                    error_code="MIN_LENGTH_VIOLATION"
                )
            if param_def.max_length and len(value) > param_def.max_length:
                return MCPToolResult.error_result(
                    error=f"Parameter '{param_def.name}' must be at most {param_def.max_length} characters",
                    error_code="MAX_LENGTH_VIOLATION"
                )
            if param_def.pattern:
                import re
                if not re.match(param_def.pattern, value):
                    return MCPToolResult.error_result(
                        error=f"Parameter '{param_def.name}' does not match required pattern",
                        error_code="PATTERN_MISMATCH"
                    )
        
        # Numeric constraints
        if isinstance(value, (int, float)):
            if param_def.minimum is not None and value < param_def.minimum:
                return MCPToolResult.error_result(
                    error=f"Parameter '{param_def.name}' must be at least {param_def.minimum}",
                    error_code="MINIMUM_VIOLATION"
                )
            if param_def.maximum is not None and value > param_def.maximum:
                return MCPToolResult.error_result(
                    error=f"Parameter '{param_def.name}' must be at most {param_def.maximum}",
                    error_code="MAXIMUM_VIOLATION"
                )
        
        return MCPToolResult.success_result(True)
    
    async def get_tool_definition(self, tool_name: str) -> Optional[MCPToolDefinition]:
        """
        Get the definition for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Optional[MCPToolDefinition]: Tool definition if found
        """
        # This should be implemented by subclasses
        return None


class MCPToolHandler(RequestHandler):
    """
    Handler for MCP tool-related requests.
    
    This handler processes tool discovery and execution requests
    according to the MCP specification.
    """
    
    def __init__(self, tool_executor: ToolExecutor):
        """
        Initialize tool handler.
        
        Args:
            tool_executor: Tool executor instance
        """
        super().__init__(supported_methods=["tools/list", "tools/call"])
        self.tool_executor = tool_executor
    
    async def handle_request(self, message) -> Optional["MCPResponse"]:
        """
        Handle tool-related requests.
        
        Args:
            message: The request message
            
        Returns:
            Optional[MCPResponse]: Response message
        """
        from mindflow_backend.schemas.mcp.base import MCPResponse, MCPError, MCPErrorCode
        
        if message.method == "tools/list":
            return await self._handle_list_tools(message)
        elif message.method == "tools/call":
            return await self._handle_call_tool(message)
        else:
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Unknown method: {message.method}"
                )
            )
    
    async def _handle_list_tools(self, message) -> "MCPResponse":
        """
        Handle tools/list request.
        
        Args:
            message: The tools/list request
            
        Returns:
            MCPResponse: Tools list response
        """
        from mindflow_backend.schemas.mcp.base import MCPResponse
        
        try:
            tools = await self._get_available_tools()
            
            return MCPResponse(
                id=message.id,
                result={
                    "tools": [tool.model_dump() for tool in tools]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error listing tools: {e}")
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Failed to list tools: {e}"
                )
            )
    
    async def _handle_call_tool(self, message) -> "MCPResponse":
        """
        Handle tools/call request.
        
        Args:
            message: The tools/call request
            
        Returns:
            MCPResponse: Tool execution response
        """
        from mindflow_backend.schemas.mcp.base import MCPResponse, MCPError, MCPErrorCode
        
        try:
            params = message.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return MCPResponse(
                    id=message.id,
                    error=MCPError(
                        code=MCPErrorCode.INVALID_PARAMS,
                        message="Tool name is required"
                    )
                )
            
            # Execute the tool
            result = await self.tool_executor.execute(tool_name, arguments)
            
            if result.success:
                return MCPResponse(
                    id=message.id,
                    result={
                        "result": result.result,
                        "metadata": result.metadata
                    }
                )
            else:
                return MCPResponse(
                    id=message.id,
                    error=MCPError(
                        code=MCPErrorCode.INTERNAL_ERROR,
                        message=result.error or "Tool execution failed"
                    )
                )
                
        except Exception as e:
            self.logger.error(f"Error calling tool: {e}")
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Failed to call tool: {e}"
                )
            )
    
    async def _get_available_tools(self) -> List[MCPToolDefinition]:
        """
        Get list of available tools.
        
        Returns:
            List[MCPToolDefinition]: Available tools
        """
        # This should be implemented by subclasses or configured
        # For now, return empty list
        return []


class SimpleToolExecutor(ToolExecutor):
    """
    Simple tool executor with basic tool implementations.
    
    This executor provides example tools and can be extended
    with custom tool implementations.
    """
    
    def __init__(self, tools: Optional[Dict[str, Callable]] = None):
        """
        Initialize simple tool executor.
        
        Args:
            tools: Dictionary of tool name to function mapping
        """
        super().__init__()
        self.tools = tools or {}
        self._tool_definitions: Dict[str, MCPToolDefinition] = {}
    
    def register_tool(self, name: str, func: Callable, definition: MCPToolDefinition) -> None:
        """
        Register a tool with the executor.
        
        Args:
            name: Tool name
            func: Tool function
            definition: Tool definition
        """
        self.tools[name] = func
        self._tool_definitions[name] = definition
        self.logger.info(f"Registered tool: {name}")
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """
        Execute a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool execution arguments
            
        Returns:
            MCPToolResult: Execution result
        """
        try:
            if tool_name not in self.tools:
                return MCPToolResult.error_result(
                    error=f"Tool '{tool_name}' not found",
                    error_code="TOOL_NOT_FOUND"
                )
            
            # Get tool function
            tool_func = self.tools[tool_name]
            
            # Validate arguments
            validation_result = await self.validate_arguments(tool_name, arguments)
            if not validation_result.success:
                return validation_result
            
            # Execute the tool
            start_time = asyncio.get_event_loop().time()
            
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**arguments)
            else:
                result = tool_func(**arguments)
            
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return MCPToolResult.success_result(
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Error executing tool '{tool_name}': {e}")
            return MCPToolResult.error_result(
                error=str(e),
                error_code="EXECUTION_ERROR"
            )
    
    async def get_tool_definition(self, tool_name: str) -> Optional[MCPToolDefinition]:
        """
        Get the definition for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Optional[MCPToolDefinition]: Tool definition if found
        """
        return self._tool_definitions.get(tool_name)
