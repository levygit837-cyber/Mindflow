"""
MCP Client Interfaces

Client-side implementations for MCP protocol communication.
Provides high-level client functionality with automatic transport selection,
connection management, and protocol handling.
"""

from .client import MCPClient, MCPClientConfig, MCPClientError, MCPClientState
from .manager import MCPClientManager, MCPClientPool

__all__ = [
    "MCPClient",
    "MCPClientConfig", 
    "MCPClientState",
    "MCPClientError",
    "MCPClientManager",
    "MCPClientPool",
]
