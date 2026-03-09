"""
MCP Client Implementation

High-level MCP client with automatic transport management,
protocol handling, and connection lifecycle management.
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union
import uuid

from mindflow_backend.schemas.mcp.base import (
    MCPMessage, MCPRequest, MCPResponse, MCPError, MCPErrorCode,
    MCPInitializeParams, MCPInitializeResult, MCPClientInfo, MCPCapability,
    MCPVersion
)
from mindflow_backend.schemas.mcp.transport import (
    MCPTransportConfig, StdioConfig, HTTPConfig, WebSocketConfig, TransportType
)
from mindflow_backend.schemas.mcp.tools import (
    MCPToolDefinition, MCPToolCall, MCPToolResult, MCPToolExecutionRequest
)
from mindflow_backend.schemas.mcp.resources import (
    MCPResourceDefinition, MCPResourceRequest, MCPResourceResult
)
from mindflow_backend.interfaces.mcp.transport import (
    MCPTransport, StdioTransport, HTTPTransport, WebSocketTransport,
    TransportError, ConnectionError
)


class MCPClientState(str, Enum):
    """MCP client connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    INITIALIZED = "initialized"
    ERROR = "error"
    CLOSING = "closing"


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPClientConfig:
    """Configuration for MCP client."""
    
    def __init__(
        self,
        transport_config: MCPTransportConfig,
        client_info: Optional[MCPClientInfo] = None,
        capabilities: Optional[List[MCPCapability]] = None,
        auto_reconnect: bool = True,
        reconnect_delay: float = 1.0,
        max_reconnect_attempts: int = 5,
        request_timeout: float = 30.0,
    ):
        """
        Initialize MCP client configuration.
        
        Args:
            transport_config: Transport configuration
            client_info: Client information
            capabilities: Client capabilities
            auto_reconnect: Whether to automatically reconnect
            reconnect_delay: Delay between reconnection attempts
            max_reconnect_attempts: Maximum reconnection attempts
            request_timeout: Default request timeout
        """
        self.transport_config = transport_config
        self.client_info = client_info or MCPClientInfo(
            name="MindFlow MCP Client",
            version="1.0.0"
        )
        self.capabilities = capabilities or []
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.request_timeout = request_timeout


class MCPClient:
    """
    High-level MCP client with automatic transport management and protocol handling.
    
    This client handles the complete MCP protocol lifecycle including initialization,
    tool execution, resource access, and automatic reconnection.
    """
    
    def __init__(self, config: MCPClientConfig):
        """
        Initialize MCP client.
        
        Args:
            config: Client configuration
        """
        self.config = config
        self.state = MCPClientState.DISCONNECTED
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Transport management
        self.transport: Optional[MCPTransport] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        
        # Protocol state
        self._initialize_result: Optional[MCPInitializeResult] = None
        self._server_capabilities: List[MCPCapability] = []
        self._available_tools: List[MCPToolDefinition] = []
        self._available_resources: List[MCPResourceDefinition] = []
        
        # Request handling
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_counter = 0
        
        # Event handlers
        self._on_connected: Optional[Callable[[], Awaitable[None]]] = None
        self._on_disconnected: Optional[Callable[[], Awaitable[None]]] = None
        self._on_error: Optional[Callable[[Exception], Awaitable[None]]] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self.state in [MCPClientState.CONNECTED, MCPClientState.INITIALIZED]
    
    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self.state == MCPClientState.INITIALIZED
    
    @property
    def server_info(self) -> Optional[MCPInitializeResult]:
        """Get server information from initialization."""
        return self._initialize_result
    
    @property
    def available_tools(self) -> List[MCPToolDefinition]:
        """Get list of available tools from server."""
        return self._available_tools.copy()
    
    @property
    def available_resources(self) -> List[MCPResourceDefinition]:
        """Get list of available resources from server."""
        return self._available_resources.copy()
    
    def set_event_handlers(
        self,
        on_connected: Optional[Callable[[], Awaitable[None]]] = None,
        on_disconnected: Optional[Callable[[], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
    ) -> None:
        """
        Set event handlers for client events.
        
        Args:
            on_connected: Handler for connection events
            on_disconnected: Handler for disconnection events
            on_error: Handler for error events
        """
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._on_error = on_error
    
    async def connect(self) -> None:
        """
        Connect to MCP server.
        
        Raises:
            MCPClientError: If connection fails
        """
        if self.state != MCPClientState.DISCONNECTED:
            raise MCPClientError(f"Cannot connect from state {self.state}")
        
        self.state = MCPClientState.CONNECTING
        
        try:
            # Create transport based on configuration
            self.transport = self._create_transport()
            
            # Set up message handler
            self.transport.set_message_handler(self._handle_message)
            self.transport.set_error_handler(self._handle_transport_error)
            
            # Connect transport
            await self.transport.connect()
            
            self.state = MCPClientState.CONNECTED
            self.logger.info("Connected to MCP server")
            
            # Initialize MCP protocol
            await self._initialize_protocol()
            
            # Start message listener
            asyncio.create_task(self.transport.start_listening())
            
            # Call connected handler
            if self._on_connected:
                await self._on_connected()
                
        except Exception as e:
            self.state = MCPClientState.ERROR
            await self._cleanup()
            raise MCPClientError(f"Failed to connect: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.state == MCPClientState.DISCONNECTED:
            return
        
        self.state = MCPClientState.CLOSING
        
        # Cancel reconnection task
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        
        await self._cleanup()
        self.state = MCPClientState.DISCONNECTED
        
        self.logger.info("Disconnected from MCP server")
        
        # Call disconnected handler
        if self._on_disconnected:
            await self._on_disconnected()
    
    async def list_tools(self) -> List[MCPToolDefinition]:
        """
        Get list of available tools from server.
        
        Returns:
            List[MCPToolDefinition]: Available tools
            
        Raises:
            MCPClientError: If request fails
        """
        if not self.is_initialized:
            raise MCPClientError("Client is not initialized")
        
        request = MCPRequest(
            method="tools/list",
            id=self._generate_request_id()
        )
        
        response = await self._send_request(request)
        
        if response.error:
            raise MCPClientError(f"Failed to list tools: {response.error.message}")
        
        tools_data = response.result.get("tools", [])
        self._available_tools = [
            MCPToolDefinition.model_validate(tool_data) for tool_data in tools_data
        ]
        
        return self._available_tools
    
    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """
        Execute a tool on the server.
        
        Args:
            tool_call: Tool execution request
            
        Returns:
            MCPToolResult: Tool execution result
            
        Raises:
            MCPClientError: If tool execution fails
        """
        if not self.is_initialized:
            raise MCPClientError("Client is not initialized")
        
        request = MCPRequest(
            method="tools/call",
            params={
                "name": tool_call.tool_name,
                "arguments": tool_call.arguments
            },
            id=self._generate_request_id()
        )
        
        response = await self._send_request(request)
        
        if response.error:
            return MCPToolResult.error_result(
                error=response.error.message,
                error_code=str(response.error.code)
            )
        
        result_data = response.result
        return MCPToolResult.success_result(result_data.get("result"))
    
    async def list_resources(self) -> List[MCPResourceDefinition]:
        """
        Get list of available resources from server.
        
        Returns:
            List[MCPResourceDefinition]: Available resources
            
        Raises:
            MCPClientError: If request fails
        """
        if not self.is_initialized:
            raise MCPClientError("Client is not initialized")
        
        request = MCPRequest(
            method="resources/list",
            id=self._generate_request_id()
        )
        
        response = await self._send_request(request)
        
        if response.error:
            raise MCPClientError(f"Failed to list resources: {response.error.message}")
        
        resources_data = response.result.get("resources", [])
        self._available_resources = [
            MCPResourceDefinition.model_validate(resource_data) for resource_data in resources_data
        ]
        
        return self._available_resources
    
    async def read_resource(self, resource_uri: str) -> MCPResourceResult:
        """
        Read a resource from the server.
        
        Args:
            resource_uri: URI of resource to read
            
        Returns:
            MCPResourceResult: Resource read result
            
        Raises:
            MCPClientError: If resource read fails
        """
        if not self.is_initialized:
            raise MCPClientError("Client is not initialized")
        
        request = MCPRequest(
            method="resources/read",
            params={"uri": resource_uri},
            id=self._generate_request_id()
        )
        
        response = await self._send_request(request)
        
        if response.error:
            return MCPResourceResult.error_result(
                error=response.error.message,
                error_code=str(response.error.code)
            )
        
        result_data = response.result
        return MCPResourceResult.success_result(result_data.get("contents"))
    
    def _create_transport(self) -> MCPTransport:
        """Create transport based on configuration."""
        transport_config = self.config.transport_config
        
        if isinstance(transport_config, StdioConfig):
            return StdioTransport(transport_config)
        elif isinstance(transport_config, HTTPConfig):
            return HTTPTransport(transport_config)
        elif isinstance(transport_config, WebSocketConfig):
            return WebSocketTransport(transport_config)
        else:
            raise MCPClientError(f"Unsupported transport type: {type(transport_config)}")
    
    async def _initialize_protocol(self) -> None:
        """Initialize MCP protocol with server."""
        init_params = MCPInitializeParams(
            protocol_version=MCPVersion.LATEST,
            capabilities=self.config.capabilities,
            client_info=self.config.client_info
        )
        
        request = MCPRequest(
            method="initialize",
            params=init_params.model_dump(),
            id=self._generate_request_id()
        )
        
        response = await self._send_request(request)
        
        if response.error:
            raise MCPClientError(f"Initialization failed: {response.error.message}")
        
        # Parse initialization result
        self._initialize_result = MCPInitializeResult.model_validate(response.result)
        self._server_capabilities = self._initialize_result.capabilities
        
        self.state = MCPClientState.INITIALIZED
        self.logger.info("MCP protocol initialized")
    
    async def _send_request(self, request: MCPRequest, timeout: Optional[float] = None) -> MCPResponse:
        """
        Send a request and wait for response.
        
        Args:
            request: Request to send
            timeout: Optional timeout
            
        Returns:
            MCPResponse: Response from server
        """
        if not self.transport or not self.is_connected:
            raise MCPClientError("Not connected to server")
        
        timeout = timeout or self.config.request_timeout
        
        try:
            response = await self.transport.send_and_wait(request, timeout)
            return MCPResponse.model_validate(response.model_dump())
        except Exception as e:
            raise MCPClientError(f"Request failed: {e}")
    
    async def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message from transport."""
        try:
            # Check if this is a response to a pending request
            if message.id and message.id in self._pending_requests:
                future = self._pending_requests.pop(message.id)
                if not future.done():
                    future.set_result(message)
                return
            
            # Handle server-initiated messages (notifications, etc.)
            if message.method and not message.id:
                await self._handle_notification(message)
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def _handle_notification(self, message: MCPMessage) -> None:
        """Handle server notification messages."""
        # Handle different notification types
        if message.method == "notifications/tools/list_changed":
            # Tool list changed, refresh
            await self.list_tools()
        elif message.method == "notifications/resources/list_changed":
            # Resource list changed, refresh
            await self.list_resources()
        else:
            self.logger.debug(f"Unhandled notification: {message.method}")
    
    async def _handle_transport_error(self, error: Exception) -> None:
        """Handle transport errors."""
        self.logger.error(f"Transport error: {error}")
        
        # Update state
        if self.state not in [MCPClientState.DISCONNECTED, MCPClientState.CLOSING]:
            self.state = MCPClientState.ERROR
        
        # Call error handler
        if self._on_error:
            await self._on_error(error)
        
        # Attempt reconnection if enabled
        if self.config.auto_reconnect and self.state == MCPClientState.ERROR:
            if not self._reconnect_task or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect to server."""
        for attempt in range(self.config.max_reconnect_attempts):
            try:
                self.logger.info(f"Reconnection attempt {attempt + 1}/{self.config.max_reconnect_attempts}")
                
                # Wait before attempting reconnection
                await asyncio.sleep(self.config.reconnect_delay)
                
                # Clean up existing connection
                await self._cleanup()
                
                # Attempt to reconnect
                await self.connect()
                self.logger.info("Reconnection successful")
                return
                
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
        
        self.logger.error("All reconnection attempts failed")
        self.state = MCPClientState.DISCONNECTED
    
    async def _cleanup(self) -> None:
        """Clean up transport and related resources."""
        if self.transport:
            try:
                await self.transport.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting transport: {e}")
            finally:
                self.transport = None
        
        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(MCPClientError("Connection closed"))
        self._pending_requests.clear()
        
        # Reset protocol state
        self._initialize_result = None
        self._server_capabilities = []
        self._available_tools = []
        self._available_resources = []
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        self._request_counter += 1
        return f"client_req_{self._request_counter}_{uuid.uuid4().hex[:8]}"
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
