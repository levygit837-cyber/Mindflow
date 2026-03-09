"""
MCP (Model Context Protocol) Interfaces Module

This module contains all interface implementations for the Model Context Protocol
in the MindFlow system. It provides transport layer abstractions, client/server
implementations, and protocol handlers for different communication methods.
"""

from .transport import (
    MCPTransport,
    StdioTransport,
    HTTPTransport,
    WebSocketTransport,
    TransportError,
    ConnectionError
)

from .client import (
    MCPClient,
    MCPClientConfig,
    MCPClientState
)

from .server import (
    MCPServer,
    MCPServerConfig,
    MCPServerState,
    MCPServerHandler
)

from .handlers import (
    MCPMessageHandler,
    MCPToolHandler,
    MCPResourceHandler,
    MCPErrorHandler
)

__all__ = [
    # Transport interfaces
    "MCPTransport",
    "StdioTransport",
    "HTTPTransport",
    "WebSocketTransport",
    "TransportError",
    "ConnectionError",
    
    # Client interfaces
    "MCPClient",
    "MCPClientConfig",
    "MCPClientState",
    
    # Server interfaces
    "MCPServer",
    "MCPServerConfig",
    "MCPServerState",
    "MCPServerHandler",
    
    # Handler interfaces
    "MCPMessageHandler",
    "MCPToolHandler",
    "MCPResourceHandler",
    "MCPErrorHandler",
]
