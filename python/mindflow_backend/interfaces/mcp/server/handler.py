"""
MCP Server Handler

Handler for processing MCP messages and managing individual client connections.
Implements the MCP protocol logic for initialization, tool execution, and resource access.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Awaitable

from mindflow_backend.schemas.mcp.base import (
    MCPMessage, MCPRequest, MCPResponse, MCPError, MCPErrorCode,
    MCPInitializeParams, MCPInitializeResult, MCPServerInfo, MCPCapability,
    MCPVersion
)
from mindflow_backend.schemas.mcp.tools import MCPToolDefinition, MCPToolResult
from mindflow_backend.schemas.mcp.resources import MCPResourceDefinition, MCPResourceResult


class BaseMCPHandler:
    """Base class for MCP message handlers."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")


class MCPToolHandler(BaseMCPHandler):
    """Handler for MCP tool-related operations."""
    
    def __init__(self, server: "MCPServer"):
        super().__init__()
        self.server = server
    
    async def list_tools(self) -> List[MCPToolDefinition]:
        """
        Get list of available tools.
        
        Returns:
            List[MCPToolDefinition]: Available tools
        """
        return self.server.available_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
            
        Returns:
            MCPToolResult: Execution result
        """
        if self.server._tool_handler:
            try:
                return await self.server._tool_handler(tool_name, arguments)
            except Exception as e:
                return MCPToolResult.error_result(
                    error=str(e),
                    error_code="EXECUTION_ERROR"
                )
        else:
            return MCPToolResult.error_result(
                error="No tool handler configured",
                error_code="NO_HANDLER"
            )


class MCPResourceHandler(BaseMCPHandler):
    """Handler for MCP resource-related operations."""
    
    def __init__(self, server: "MCPServer"):
        super().__init__()
        self.server = server
    
    async def list_resources(self) -> List[MCPResourceDefinition]:
        """
        Get list of available resources.
        
        Returns:
            List[MCPResourceDefinition]: Available resources
        """
        return self.server.available_resources
    
    async def read_resource(self, resource_uri: str) -> MCPResourceResult:
        """
        Read a resource.
        
        Args:
            resource_uri: URI of resource to read
            
        Returns:
            MCPResourceResult: Resource read result
        """
        if self.server._resource_handler:
            try:
                return await self.server._resource_handler(resource_uri, {})
            except Exception as e:
                return MCPResourceResult.error_result(
                    error=str(e),
                    error_code="READ_ERROR"
                )
        else:
            return MCPResourceResult.error_result(
                error="No resource handler configured",
                error_code="NO_HANDLER"
            )


class MCPServerHandler(BaseMCPHandler):
    """
    Handler for individual MCP client connections.
    
    This handler manages the protocol state for a single client connection
    and processes incoming messages according to the MCP specification.
    """
    
    def __init__(self, server: "MCPServer", connection_id: str):
        """
        Initialize server handler.
        
        Args:
            server: The MCP server instance
            connection_id: Unique connection identifier
        """
        super().__init__()
        self.server = server
        self.connection_id = connection_id
        self.initialized = False
        self.client_info: Optional[Dict[str, Any]] = None
        self.client_capabilities: List[MCPCapability] = []
        
        # Sub-handlers
        self.tool_handler = MCPToolHandler(server)
        self.resource_handler = MCPResourceHandler(server)
    
    async def handle_message(self, message: MCPMessage) -> Optional[MCPResponse]:
        """
        Handle an incoming MCP message.
        
        Args:
            message: The incoming message
            
        Returns:
            Optional[MCPResponse]: Response message if needed
        """
        try:
            # Handle requests
            if isinstance(message, MCPRequest) or message.method:
                return await self._handle_request(message)
            
            # Handle responses (server typically doesn't receive responses)
            elif message.result is not None or message.error is not None:
                self.logger.debug(f"Received unexpected response: {message.id}")
                return None
            
            # Invalid message
            else:
                return MCPResponse(
                    id=message.id,
                    error=MCPError(
                        code=MCPErrorCode.INVALID_REQUEST,
                        message="Invalid message format"
                    )
                )
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=str(e)
                )
            )
    
    async def _handle_request(self, message: MCPMessage) -> MCPResponse:
        """
        Handle a request message.
        
        Args:
            message: The request message
            
        Returns:
            MCPResponse: Response message
        """
        method = message.method
        
        # Check if initialization is required
        if not self.initialized and method != "initialize":
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.SERVER_NOT_INITIALIZED,
                    message="Server not initialized"
                )
            )
        
        # Handle different methods
        if method == "initialize":
            return await self._handle_initialize(message)
        elif method == "tools/list":
            return await self._handle_list_tools(message)
        elif method == "tools/call":
            return await self._handle_call_tool(message)
        elif method == "resources/list":
            return await self._handle_list_resources(message)
        elif method == "resources/read":
            return await self._handle_read_resource(message)
        else:
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Unknown method: {method}"
                )
            )
    
    async def _handle_initialize(self, message: MCPMessage) -> MCPResponse:
        """
        Handle initialization request.
        
        Args:
            message: The initialize request
            
        Returns:
            MCPResponse: Initialize response
        """
        try:
            # Parse initialization parameters
            params = message.params or {}
            init_params = MCPInitializeParams.model_validate(params)
            
            # Store client information
            self.client_info = init_params.client_info.model_dump()
            self.client_capabilities = init_params.capabilities
            
            # Create initialization result
            init_result = MCPInitializeResult(
                protocol_version=MCPVersion.LATEST,
                capabilities=self.server.config.capabilities,
                server_info=self.server.config.server_info
            )
            
            self.initialized = True
            self.logger.info(f"Client {self.connection_id} initialized")
            
            return MCPResponse(
                id=message.id,
                result=init_result.model_dump()
            )
            
        except Exception as e:
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INVALID_PARAMS,
                    message=f"Invalid initialization parameters: {e}"
                )
            )
    
    async def _handle_list_tools(self, message: MCPMessage) -> MCPResponse:
        """
        Handle tools/list request.
        
        Args:
            message: The tools/list request
            
        Returns:
            MCPResponse: Tools list response
        """
        try:
            tools = await self.tool_handler.list_tools()
            
            return MCPResponse(
                id=message.id,
                result={
                    "tools": [tool.model_dump() for tool in tools]
                }
            )
            
        except Exception as e:
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Failed to list tools: {e}"
                )
            )
    
    async def _handle_call_tool(self, message: MCPMessage) -> MCPResponse:
        """
        Handle tools/call request.
        
        Args:
            message: The tools/call request
            
        Returns:
            MCPResponse: Tool execution response
        """
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
            
            result = await self.tool_handler.call_tool(tool_name, arguments)
            
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
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Failed to call tool: {e}"
                )
            )
    
    async def _handle_list_resources(self, message: MCPMessage) -> MCPResponse:
        """
        Handle resources/list request.
        
        Args:
            message: The resources/list request
            
        Returns:
            MCPResponse: Resources list response
        """
        try:
            resources = await self.resource_handler.list_resources()
            
            return MCPResponse(
                id=message.id,
                result={
                    "resources": [resource.model_dump() for resource in resources]
                }
            )
            
        except Exception as e:
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Failed to list resources: {e}"
                )
            )
    
    async def _handle_read_resource(self, message: MCPMessage) -> MCPResponse:
        """
        Handle resources/read request.
        
        Args:
            message: The resources/read request
            
        Returns:
            MCPResponse: Resource read response
        """
        try:
            params = message.params or {}
            resource_uri = params.get("uri")
            
            if not resource_uri:
                return MCPResponse(
                    id=message.id,
                    error=MCPError(
                        code=MCPErrorCode.INVALID_PARAMS,
                        message="Resource URI is required"
                    )
                )
            
            result = await self.resource_handler.read_resource(resource_uri)
            
            if result.success:
                return MCPResponse(
                    id=message.id,
                    result={
                        "contents": result.data,
                        "metadata": result.metadata
                    }
                )
            else:
                return MCPResponse(
                    id=message.id,
                    error=MCPError(
                        code=MCPErrorCode.INTERNAL_ERROR,
                        message=result.error or "Resource read failed"
                    )
                )
                
        except Exception as e:
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Failed to read resource: {e}"
                )
            )
