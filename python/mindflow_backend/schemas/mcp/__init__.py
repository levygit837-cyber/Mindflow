"""
MCP (Model Context Protocol) Schemas Module

This module contains all schema definitions for the Model Context Protocol implementation
in the MindFlow system. It provides standardized data structures for MCP communication,
including requests, responses, tools, resources, and transport layer abstractions.
"""

from .base import (
    MCPRequest,
    MCPResponse,
    MCPError,
    MCPMessage,
    MCPVersion,
    MCPErrorCode,
    JSONRPCMessage
)

from .transport import (
    MCPTransportConfig,
    StdioConfig,
    HTTPConfig,
    WebSocketConfig,
    TransportType
)

from .tools import (
    MCPTool,
    MCPToolDefinition,
    MCPToolResult,
    MCPToolParameter,
    MCPToolCall
)

from .resources import (
    MCPResource,
    MCPResourceDefinition,
    MCPResourceResult,
    MCPResourceTemplate
)

__all__ = [
    # Base schemas
    "MCPRequest",
    "MCPResponse", 
    "MCPError",
    "MCPMessage",
    "MCPVersion",
    "MCPErrorCode",
    "JSONRPCMessage",
    
    # Transport schemas
    "MCPTransportConfig",
    "StdioConfig",
    "HTTPConfig", 
    "WebSocketConfig",
    "TransportType",
    
    # Tool schemas
    "MCPTool",
    "MCPToolDefinition",
    "MCPToolResult",
    "MCPToolParameter",
    "MCPToolCall",
    
    # Resource schemas
    "MCPResource",
    "MCPResourceDefinition", 
    "MCPResourceResult",
    "MCPResourceTemplate",
]
