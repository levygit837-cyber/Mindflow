"""
MCP Transport Configuration Schemas

Configuration schemas for different MCP transport mechanisms including
stdio, HTTP, and WebSocket connections.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """Supported transport types."""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MCPTransportConfig(BaseModel):
    """Base transport configuration."""
    transport_type: TransportType = Field(description="Type of transport")
    timeout: Optional[int] = Field(default=30, description="Connection timeout in seconds")
    retries: Optional[int] = Field(default=3, description="Number of retry attempts")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional headers")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Transport metadata")


class StdioConfig(MCPTransportConfig):
    """Configuration for stdio transport."""
    transport_type: TransportType = Field(default=TransportType.STDIO, const=True)
    command: List[str] = Field(description="Command to execute for stdio transport")
    working_directory: Optional[str] = Field(default=None, description="Working directory")
    environment: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    stdin_encoding: Optional[str] = Field(default="utf-8", description=" stdin encoding")
    stdout_encoding: Optional[str] = Field(default="utf-8", description=" stdout encoding")
    stderr_encoding: Optional[str] = Field(default="utf-8", description=" stderr encoding")


class HTTPConfig(MCPTransportConfig):
    """Configuration for HTTP transport."""
    transport_type: TransportType = Field(default=TransportType.HTTP, const=True)
    url: str = Field(description="HTTP server URL")
    method: Optional[str] = Field(default="POST", description="HTTP method")
    verify_ssl: Optional[bool] = Field(default=True, description="Verify SSL certificates")
    follow_redirects: Optional[bool] = Field(default=True, description="Follow HTTP redirects")
    max_redirects: Optional[int] = Field(default=5, description="Maximum redirect count")
    keep_alive: Optional[bool] = Field(default=True, description="Use HTTP keep-alive")
    chunk_size: Optional[int] = Field(default=8192, description="HTTP chunk size")


class WebSocketConfig(MCPTransportConfig):
    """Configuration for WebSocket transport."""
    transport_type: TransportType = Field(default=TransportType.WEBSOCKET, const=True)
    url: str = Field(description="WebSocket server URL")
    subprotocols: Optional[List[str]] = Field(default_factory=list, description="WebSocket subprotocols")
    origin: Optional[str] = Field(default=None, description="WebSocket origin header")
    ping_interval: Optional[int] = Field(default=20, description="Ping interval in seconds")
    ping_timeout: Optional[int] = Field(default=10, description="Ping timeout in seconds")
    close_timeout: Optional[int] = Field(default=10, description="Close timeout in seconds")
    max_size: Optional[int] = Field(default=2**20, description="Maximum message size in bytes")
    max_queue: Optional[int] = Field(default=32, description="Maximum queue size")


class MCPConnectionInfo(BaseModel):
    """Information about an MCP connection."""
    transport_type: TransportType = Field(description="Transport type")
    endpoint: str = Field(description="Connection endpoint")
    status: str = Field(description="Connection status")
    last_activity: Optional[str] = Field(default=None, description="Last activity timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Connection metadata")


class MCPTransportMetrics(BaseModel):
    """Transport performance metrics."""
    messages_sent: int = Field(default=0, description="Number of messages sent")
    messages_received: int = Field(default=0, description="Number of messages received")
    bytes_sent: int = Field(default=0, description="Number of bytes sent")
    bytes_received: int = Field(default=0, description="Number of bytes received")
    errors: int = Field(default=0, description="Number of errors")
    average_response_time: Optional[float] = Field(default=None, description="Average response time in ms")
    uptime: Optional[float] = Field(default=None, description="Connection uptime in seconds")
