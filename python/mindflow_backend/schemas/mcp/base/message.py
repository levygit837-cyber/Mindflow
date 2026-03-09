"""
Base MCP message schemas following the Model Context Protocol specification.

This module defines the core message structures used throughout the MCP implementation,
including JSON-RPC 2.0 compliant messages, error handling, and protocol versioning.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MCPVersion(str, Enum):
    """Supported MCP protocol versions."""
    LATEST = "2024-11-05"
    V2024_11_05 = "2024-11-05"


class MCPErrorCode(int, Enum):
    """Standard MCP error codes as defined in the specification."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes
    SERVER_NOT_INITIALIZED = -32002
    UNKNOWN_ERROR = -32001


class JSONRPCMessage(BaseModel):
    """Base JSON-RPC 2.0 message structure."""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(default=None, description="Request identifier")


class MCPError(BaseModel):
    """MCP error message structure."""
    code: int = Field(description="Error code from MCPErrorCode enum")
    message: str = Field(description="Human-readable error description")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional error data")


class MCPMessage(JSONRPCMessage):
    """Base MCP message with optional method and result/error fields."""
    method: Optional[str] = Field(default=None, description="Method name for requests")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Method parameters")
    result: Optional[Any] = Field(default=None, description="Method result for responses")
    error: Optional[MCPError] = Field(default=None, description="Error information")


class MCPRequest(MCPMessage):
    """MCP request message."""
    method: str = Field(description="Method name to invoke")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Method parameters")
    
    class Config:
        json_encoders = {
            # Custom encoding if needed
        }


class MCPResponse(MCPMessage):
    """MCP response message."""
    result: Optional[Any] = Field(default=None, description="Method result")
    error: Optional[MCPError] = Field(default=None, description="Error information")
    
    @classmethod
    def success(cls, request_id: Union[str, int], result: Any) -> "MCPResponse":
        """Create a successful response."""
        return cls(id=request_id, result=result)
    
    @classmethod
    def error(cls, request_id: Union[str, int], error: MCPError) -> "MCPResponse":
        """Create an error response."""
        return cls(id=request_id, error=error)


class MCPCapability(BaseModel):
    """MCP capability description."""
    name: str = Field(description="Capability name")
    version: Optional[str] = Field(default=None, description="Capability version")
    description: Optional[str] = Field(default=None, description="Capability description")


class MCPClientInfo(BaseModel):
    """MCP client information."""
    name: str = Field(description="Client name")
    version: str = Field(description="Client version")
    protocol_version: MCPVersion = Field(default=MCPVersion.LATEST, description="Protocol version")


class MCPServerInfo(BaseModel):
    """MCP server information."""
    name: str = Field(description="Server name")
    version: str = Field(description="Server version")
    protocol_version: MCPVersion = Field(default=MCPVersion.LATEST, description="Protocol version")
    capabilities: List[MCPCapability] = Field(default_factory=list, description="Server capabilities")


class MCPInitializeParams(BaseModel):
    """Parameters for initialize request."""
    protocol_version: MCPVersion = Field(description="Protocol version")
    capabilities: List[MCPCapability] = Field(default_factory=list, description="Client capabilities")
    client_info: MCPClientInfo = Field(description="Client information")


class MCPInitializeResult(BaseModel):
    """Result for initialize response."""
    protocol_version: MCPVersion = Field(description="Negotiated protocol version")
    capabilities: List[MCPCapability] = Field(default_factory=list, description="Server capabilities")
    server_info: MCPServerInfo = Field(description="Server information")
