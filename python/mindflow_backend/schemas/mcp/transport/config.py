"""
MCP Transport Configuration Schemas

Configuration schemas for different MCP transport mechanisms including
stdio, HTTP, and WebSocket connections.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """Supported transport types."""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MCPTransportConfig(BaseModel):
    """Base transport configuration."""
    transport_type: TransportType = Field(description="Type of transport")
    timeout: int | None = Field(default=30, description="Connection timeout in seconds")
    retries: int | None = Field(default=3, description="Number of retry attempts")
    headers: dict[str, str] | None = Field(default_factory=dict, description="Additional headers")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Transport metadata")


class StdioConfig(MCPTransportConfig):
    """Configuration for stdio transport."""
    transport_type: TransportType = Field(default=TransportType.STDIO, const=True)
    command: list[str] = Field(description="Command to execute for stdio transport")
    working_directory: str | None = Field(default=None, description="Working directory")
    environment: dict[str, str] | None = Field(default_factory=dict, description="Environment variables")
    stdin_encoding: str | None = Field(default="utf-8", description=" stdin encoding")
    stdout_encoding: str | None = Field(default="utf-8", description=" stdout encoding")
    stderr_encoding: str | None = Field(default="utf-8", description=" stderr encoding")


class HTTPConfig(MCPTransportConfig):
    """Configuration for HTTP transport."""
    transport_type: TransportType = Field(default=TransportType.HTTP, const=True)
    url: str = Field(description="HTTP server URL")
    method: str | None = Field(default="POST", description="HTTP method")
    verify_ssl: bool | None = Field(default=True, description="Verify SSL certificates")
    follow_redirects: bool | None = Field(default=True, description="Follow HTTP redirects")
    max_redirects: int | None = Field(default=5, description="Maximum redirect count")
    keep_alive: bool | None = Field(default=True, description="Use HTTP keep-alive")
    chunk_size: int | None = Field(default=8192, description="HTTP chunk size")


class WebSocketConfig(MCPTransportConfig):
    """Configuration for WebSocket transport."""
    transport_type: TransportType = Field(default=TransportType.WEBSOCKET, const=True)
    url: str = Field(description="WebSocket server URL")
    subprotocols: list[str] | None = Field(default_factory=list, description="WebSocket subprotocols")
    origin: str | None = Field(default=None, description="WebSocket origin header")
    ping_interval: int | None = Field(default=20, description="Ping interval in seconds")
    ping_timeout: int | None = Field(default=10, description="Ping timeout in seconds")
    close_timeout: int | None = Field(default=10, description="Close timeout in seconds")
    max_size: int | None = Field(default=2**20, description="Maximum message size in bytes")
    max_queue: int | None = Field(default=32, description="Maximum queue size")


class MCPConnectionInfo(BaseModel):
    """Information about an MCP connection."""
    transport_type: TransportType = Field(description="Transport type")
    endpoint: str = Field(description="Connection endpoint")
    status: str = Field(description="Connection status")
    last_activity: str | None = Field(default=None, description="Last activity timestamp")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Connection metadata")


class MCPTransportMetrics(BaseModel):
    """Transport performance metrics."""
    messages_sent: int = Field(default=0, description="Number of messages sent")
    messages_received: int = Field(default=0, description="Number of messages received")
    bytes_sent: int = Field(default=0, description="Number of bytes sent")
    bytes_received: int = Field(default=0, description="Number of bytes received")
    errors: int = Field(default=0, description="Number of errors")
    average_response_time: float | None = Field(default=None, description="Average response time in ms")
    uptime: float | None = Field(default=None, description="Connection uptime in seconds")
