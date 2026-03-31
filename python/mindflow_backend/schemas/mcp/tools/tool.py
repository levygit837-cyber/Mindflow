"""
MCP Tool Schemas

Definitions for MCP tools, parameters, execution results, and tool management
following the Model Context Protocol specification.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MCPParameterType(str, Enum):
    """Supported parameter types for MCP tools."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


class MCPToolParameter(BaseModel):
    """Parameter definition for MCP tools."""
    name: str = Field(description="Parameter name")
    description: str = Field(description="Parameter description")
    type: MCPParameterType = Field(description="Parameter type")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any | None = Field(default=None, description="Default value")
    enum: list[Any] | None = Field(default=None, description="Allowed values")
    format: str | None = Field(default=None, description="Parameter format (e.g., 'date-time', 'email')")
    pattern: str | None = Field(default=None, description="Regex pattern for string validation")
    minimum: int | float | None = Field(default=None, description="Minimum value for numbers")
    maximum: int | float | None = Field(default=None, description="Maximum value for numbers")
    min_length: int | None = Field(default=None, description="Minimum length for strings")
    max_length: int | None = Field(default=None, description="Maximum length for strings")
    items: dict[str, Any] | None = Field(default=None, description="Schema for array items")
    properties: dict[str, "MCPToolParameter"] | None = Field(default=None, description="Object properties")
    additional_properties: bool | dict[str, Any] | None = Field(default=None, description="Additional object properties")


class MCPToolSchema(BaseModel):
    """JSON Schema definition for tool parameters."""
    type: str = Field(default="object", description="Schema type")
    properties: dict[str, MCPToolParameter] = Field(default_factory=dict, description="Parameter definitions")
    required: list[str] = Field(default_factory=list, description="Required parameter names")
    additional_properties: bool | None = Field(default=False, description="Allow additional properties")
    description: str | None = Field(default=None, description="Schema description")


class MCPToolDefinition(BaseModel):
    """Complete definition of an MCP tool."""
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    input_schema: MCPToolSchema = Field(description="Input parameter schema")
    output_schema: MCPToolSchema | None = Field(default=None, description="Output parameter schema")
    category: str | None = Field(default=None, description="Tool category")
    tags: list[str] | None = Field(default_factory=list, description="Tool tags")
    version: str | None = Field(default="1.0.0", description="Tool version")
    author: str | None = Field(default=None, description="Tool author")
    license: str | None = Field(default=None, description="Tool license")
    deprecated: bool | None = Field(default=False, description="Whether tool is deprecated")
    experimental: bool | None = Field(default=False, description="Whether tool is experimental")


class MCPToolCall(BaseModel):
    """Represents a tool execution call."""
    tool_name: str = Field(description="Name of the tool to call")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    call_id: str | None = Field(default=None, description="Unique call identifier")
    timeout: int | None = Field(default=None, description="Execution timeout in seconds")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Call metadata")


class MCPToolResult(BaseModel):
    """Result of a tool execution."""
    success: bool = Field(description="Whether execution was successful")
    result: Any | None = Field(default=None, description="Execution result")
    error: str | None = Field(default=None, description="Error message if failed")
    error_code: str | None = Field(default=None, description="Error code")
    execution_time: float | None = Field(default=None, description="Execution time in milliseconds")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Result metadata")
    
    @classmethod
    def success_result(cls, result: Any, execution_time: float | None = None) -> "MCPToolResult":
        """Create a successful result."""
        return cls(
            success=True,
            result=result,
            execution_time=execution_time
        )
    
    @classmethod
    def error_result(cls, error: str, error_code: str | None = None, execution_time: float | None = None) -> "MCPToolResult":
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            error_code=error_code,
            execution_time=execution_time
        )


class MCPTool(BaseModel):
    """Complete MCP tool with definition and execution state."""
    definition: MCPToolDefinition = Field(description="Tool definition")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    call_count: int = Field(default=0, description="Number of times tool was called")
    last_called: str | None = Field(default=None, description="Last call timestamp")
    average_execution_time: float | None = Field(default=None, description="Average execution time in ms")
    error_rate: float | None = Field(default=0.0, description="Error rate (0.0 to 1.0)")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Tool metadata")


class MCPToolList(BaseModel):
    """List of available MCP tools."""
    tools: list[MCPTool] = Field(default_factory=list, description="Available tools")
    total_count: int = Field(default=0, description="Total number of tools")
    categories: list[str] = Field(default_factory=list, description="Available categories")
    
    def __init__(self, **data):
        super().__init__(**data)
        self.total_count = len(self.tools)
        self.categories = list(set(tool.definition.category for tool in self.tools if tool.definition.category))


class MCPToolExecutionRequest(BaseModel):
    """Request to execute one or more tools."""
    tool_calls: list[MCPToolCall] = Field(description="Tool calls to execute")
    parallel: bool = Field(default=False, description="Execute tools in parallel")
    timeout: int | None = Field(default=None, description="Global timeout in seconds")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Request metadata")


class MCPToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    results: list[MCPToolResult] = Field(description="Execution results")
    total_execution_time: float | None = Field(default=None, description="Total execution time in ms")
    success_count: int = Field(default=0, description="Number of successful executions")
    error_count: int = Field(default=0, description="Number of failed executions")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Response metadata")
    
    def __init__(self, **data):
        super().__init__(**data)
        self.success_count = sum(1 for result in self.results if result.success)
        self.error_count = len(self.results) - self.success_count
