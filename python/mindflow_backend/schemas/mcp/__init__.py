"""
MCP (Model Context Protocol) Schemas Module

This module contains all schema definitions for the Model Context Protocol implementation
in the MindFlow system. It provides standardized data structures for MCP communication,
including requests, responses, tools, resources, and transport layer abstractions.
"""

from .base import (
    JSONRPCMessage,
    MCPError,
    MCPErrorCode,
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPVersion,
)
from .resources import MCPResource, MCPResourceDefinition, MCPResourceResult, MCPResourceTemplate
from .tools import MCPTool, MCPToolCall, MCPToolDefinition, MCPToolParameter, MCPToolResult
from .transport import HTTPConfig, MCPTransportConfig, StdioConfig, TransportType, WebSocketConfig

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
