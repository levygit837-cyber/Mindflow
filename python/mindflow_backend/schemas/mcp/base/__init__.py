"""
MCP Base Schemas

Core schema definitions for MCP protocol messages, requests, responses,
and error handling based on the Model Context Protocol specification.
"""

from .message import (
    JSONRPCMessage,
    MCPError,
    MCPErrorCode,
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPVersion,
)

__all__ = [
    "MCPRequest",
    "MCPResponse",
    "MCPError", 
    "MCPMessage",
    "MCPVersion",
    "MCPErrorCode",
    "JSONRPCMessage",
]
