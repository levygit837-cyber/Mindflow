"""
MCP Server Implementation

High-level MCP server with automatic transport management,
protocol handling, and connection lifecycle management.
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, Set
import uuid

from mindflow_backend.schemas.mcp.base import (
    MCPMessage, MCPRequest, MCPResponse, MCPError, MCPErrorCode,
    MCPInitializeParams, MCPInitializeResult, MCPServerInfo, MCPCapability,
    MCPVersion
)
from mindflow_backend.schemas.mcp.transport import (
    MCPTransportConfig, StdioConfig, HTTPConfig, WebSocketConfig
)
from mindflow_backend.schemas.mcp.tools import MCPToolDefinition, MCPToolResult
from mindflow_backend.schemas.mcp.resources import MCPResourceDefinition, MCPResourceResult
from mindflow_backend.interfaces.mcp.transport import (
    MCPTransport, StdioTransport, HTTPTransport, WebSocketTransport,
    TransportError, ConnectionError
)
from mindflow_backend.interfaces.mcp.server.handler import MCPServerHandler


class MCPServerState(str, Enum):
    """MCP server connection states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


class MCPServerError(Exception):
    """Base exception for MCP server errors."""
    pass


class MCPServerConfig:
    """Configuration for MCP server."""
    
    def __init__(
        self,
        transport_configs: List[MCPTransportConfig],
        server_info: Optional[MCPServerInfo] = None,
        capabilities: Optional[List[MCPCapability]] = None,
        max_connections: int = 100,
        request_timeout: float = 30.0,
        enable_logging: bool = True,
    ):
        """
        Initialize MCP server configuration.
        
        Args:
            transport_configs: List of transport configurations
            server_info: Server information
            capabilities: Server capabilities
            max_connections: Maximum concurrent connections
            request_timeout: Default request timeout
            enable_logging: Whether to enable detailed logging
        """
        self.transport_configs = transport_configs
        self.server_info = server_info or MCPServerInfo(
            name="MindFlow MCP Server",
            version="1.0.0"
        )
        self.capabilities = capabilities or []
        self.max_connections = max_connections
        self.request_timeout = request_timeout
        self.enable_logging = enable_logging


class MCPServer:
    """
    High-level MCP server with automatic transport management and protocol handling.
    
    This server handles the complete MCP protocol lifecycle including client initialization,
    tool execution, resource access, and connection management.
    """
    
    def __init__(self, config: MCPServerConfig):
        """
        Initialize MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.state = MCPServerState.STOPPED
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Transport management
        self.transports: List[MCPTransport] = []
        self._transport_tasks: List[asyncio.Task] = []
        
        # Connection management
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._connection_handlers: Dict[str, MCPServerHandler] = {}
        
        # Server handlers
        self._tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[MCPToolResult]]] = None
        self._resource_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[MCPResourceResult]]] = None
        
        # Available tools and resources
        self._available_tools: List[MCPToolDefinition] = []
        self._available_resources: List[MCPResourceDefinition] = []
        
        # Event handlers
        self._on_client_connected: Optional[Callable[[str], Awaitable[None]]] = None
        self._on_client_disconnected: Optional[Callable[[str], Awaitable[None]]] = None
        self._on_error: Optional[Callable[[Exception, Optional[str]], Awaitable[None]]] = None
    
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.state == MCPServerState.RUNNING
    
    @property
    def connection_count(self) -> int:
        """Get current number of connections."""
        return len(self._connections)
    
    @property
    def available_tools(self) -> List[MCPToolDefinition]:
        """Get list of available tools."""
        return self._available_tools.copy()
    
    @property
    def available_resources(self) -> List[MCPResourceDefinition]:
        """Get list of available resources."""
        return self._available_resources.copy()
    
    def register_tools(self, tools: List[MCPToolDefinition]) -> None:
        """
        Register available tools.
        
        Args:
            tools: List of tool definitions
        """
        self._available_tools.extend(tools)
        self.logger.info(f"Registered {len(tools)} tools")
    
    def register_resources(self, resources: List[MCPResourceDefinition]) -> None:
        """
        Register available resources.
        
        Args:
            resources: List of resource definitions
        """
        self._available_resources.extend(resources)
        self.logger.info(f"Registered {len(resources)} resources")
    
    def set_handlers(
        self,
        tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[MCPToolResult]]] = None,
        resource_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[MCPResourceResult]]] = None,
    ) -> None:
        """
        Set handlers for tools and resources.
        
        Args:
            tool_handler: Handler for tool execution
            resource_handler: Handler for resource access
        """
        self._tool_handler = tool_handler
        self._resource_handler = resource_handler
    
    def set_event_handlers(
        self,
        on_client_connected: Optional[Callable[[str], Awaitable[None]]] = None,
        on_client_disconnected: Optional[Callable[[str], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Exception, Optional[str]], Awaitable[None]]] = None,
    ) -> None:
        """
        Set event handlers for server events.
        
        Args:
            on_client_connected: Handler for client connection events
            on_client_disconnected: Handler for client disconnection events
            on_error: Handler for error events
        """
        self._on_client_connected = on_client_connected
        self._on_client_disconnected = on_client_disconnected
        self._on_error = on_error
    
    async def start(self) -> None:
        """
        Start the MCP server.
        
        Raises:
            MCPServerError: If server fails to start
        """
        if self.state != MCPServerState.STOPPED:
            raise MCPServerError(f"Cannot start server from state {self.state}")
        
        self.state = MCPServerState.STARTING
        
        try:
            # Create and start transports
            for transport_config in self.config.transport_configs:
                transport = self._create_transport(transport_config)
                self.transports.append(transport)
                
                # Set up message handler
                transport.set_message_handler(self._handle_message)
                transport.set_error_handler(self._handle_transport_error)
            
            # Start all transports
            for transport in self.transports:
                await transport.connect()
                self.logger.info(f"Transport {type(transport).__name__} connected")
            
            self.state = MCPServerState.RUNNING
            self.logger.info("MCP server started")
            
        except Exception as e:
            self.state = MCPServerState.ERROR
            await self._cleanup()
            raise MCPServerError(f"Failed to start server: {e}")
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        if self.state == MCPServerState.STOPPED:
            return
        
        self.state = MCPServerState.STOPPING
        
        await self._cleanup()
        self.state = MCPServerState.STOPPED
        
        self.logger.info("MCP server stopped")
    
    async def _create_transport(self, config: MCPTransportConfig) -> MCPTransport:
        """Create transport based on configuration."""
        if isinstance(config, StdioConfig):
            return StdioTransport(config)
        elif isinstance(config, HTTPConfig):
            return HTTPTransport(config)
        elif isinstance(config, WebSocketConfig):
            return WebSocketTransport(config)
        else:
            raise MCPServerError(f"Unsupported transport type: {type(config)}")
    
    async def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message from transport."""
        try:
            # Get or create connection ID
            connection_id = self._get_connection_id(message)
            
            # Create handler if needed
            if connection_id not in self._connection_handlers:
                handler = MCPServerHandler(self, connection_id)
                self._connection_handlers[connection_id] = handler
                self._connections[connection_id] = {
                    "connected_at": asyncio.get_event_loop().time(),
                    "message_count": 0
                }
                
                # Call connected handler
                if self._on_client_connected:
                    await self._on_client_connected(connection_id)
            
            # Update connection stats
            self._connections[connection_id]["message_count"] += 1
            
            # Handle message
            handler = self._connection_handlers[connection_id]
            response = await handler.handle_message(message)
            
            # Send response if needed
            if response and message.id:
                await self._send_response(message, response)
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            
            # Send error response
            if message.id:
                error_response = MCPResponse(
                    id=message.id,
                    error=MCPError(
                        code=MCPErrorCode.INTERNAL_ERROR,
                        message=str(e)
                    )
                )
                await self._send_response(message, error_response)
            
            # Call error handler
            if self._on_error:
                await self._on_error(e, self._get_connection_id(message))
    
    async def _send_response(self, original_message: MCPMessage, response: MCPResponse) -> None:
        """Send response message."""
        try:
            # Find the transport that should send the response
            # This is a simplified approach - in practice, you'd need to track
            # which transport received the original message
            for transport in self.transports:
                if transport.is_connected:
                    await transport.send_message(response)
                    break
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
    
    async def _handle_transport_error(self, error: Exception) -> None:
        """Handle transport errors."""
        self.logger.error(f"Transport error: {error}")
        
        # Update state
        if self.state == MCPServerState.RUNNING:
            self.state = MCPServerState.ERROR
        
        # Call error handler
        if self._on_error:
            await self._on_error(error, None)
    
    def _get_connection_id(self, message: MCPMessage) -> str:
        """Generate or get connection ID for message."""
        # This is a simplified approach - in practice, you'd want to
        # track connections more sophisticatedly
        return f"conn_{hash(str(message)) % 10000:04d}"
    
    async def _cleanup(self) -> None:
        """Clean up transports and connections."""
        # Stop transport tasks
        for task in self._transport_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._transport_tasks.clear()
        
        # Disconnect transports
        for transport in self.transports:
            try:
                await transport.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting transport: {e}")
        self.transports.clear()
        
        # Clear connections
        for connection_id in list(self._connections.keys()):
            await self._remove_connection(connection_id)
    
    async def _remove_connection(self, connection_id: str) -> None:
        """Remove a connection."""
        if connection_id in self._connections:
            del self._connections[connection_id]
        
        if connection_id in self._connection_handlers:
            del self._connection_handlers[connection_id]
        
        # Call disconnected handler
        if self._on_client_disconnected:
            await self._on_client_disconnected(connection_id)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
