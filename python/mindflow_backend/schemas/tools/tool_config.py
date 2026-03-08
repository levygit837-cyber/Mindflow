"""Tool configuration schemas for MindFlow backend.

Provides standardized schemas for tool configuration,
parameters, and metadata validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mindflow_backend.schemas.orchestration.orchestrator import AgentType


class ToolParameter(BaseModel):
    """Schema definition for a tool parameter."""
    
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, integer, boolean, array, object)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(default=None, description="Default value if not provided")
    enum: Optional[List[str]] = Field(default=None, description="Allowed values for enum parameters")
    format: Optional[str] = Field(default=None, description="Format hint (e.g., 'file-path', 'url')")
    constraints: Optional[Dict[str, Any]] = Field(default=None, description="Additional constraints")


class ToolSchema(BaseModel):
    """Complete schema definition for a tool."""
    
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    category: str = Field(..., description="Tool category (filesystem, web, system, ai, data, integration)")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    returns: Dict[str, Any] = Field(default_factory=dict, description="Return value schema")
    examples: Optional[List[Dict[str, Any]]] = Field(default=None, description="Usage examples")
    supported_agents: List[AgentType] = Field(default_factory=lambda: list(AgentType), description="Supported agent types")
    requires_backend: bool = Field(default=False, description="Whether tool requires backend")
    requires_sandbox: bool = Field(default=False, description="Whether tool requires sandbox")
    async_execution: bool = Field(default=True, description="Whether tool supports async execution")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict, description="Resource requirements")
    tags: Optional[List[str]] = Field(default=None, description="Tool tags for categorization")
    version: Optional[str] = Field(default="1.0.0", description="Tool version")
    
    class Config:
        use_enum_values = True


class ToolRegistrySchema(BaseModel):
    """Schema for tool registry configuration."""
    
    name: str = Field(..., description="Registry name")
    auto_discovery: bool = Field(default=True, description="Enable auto-discovery of tools")
    validation_enabled: bool = Field(default=True, description="Enable schema validation")
    caching_enabled: bool = Field(default=True, description="Enable result caching")
    cache_ttl_seconds: int = Field(default=300, description="Cache time-to-live in seconds")
    max_cache_size: int = Field(default=1000, description="Maximum cache size")
    permission_checking: bool = Field(default=True, description="Enable permission checking")
    execution_timeout_seconds: int = Field(default=300, description="Default execution timeout")
    metrics_enabled: bool = Field(default=True, description="Enable execution metrics")
    
    class Config:
        use_enum_values = True


class ToolConfig(BaseModel):
    """Configuration for individual tool instances."""
    
    tool_name: str = Field(..., description="Tool name")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    timeout_seconds: Optional[int] = Field(default=None, description="Custom timeout")
    retry_count: int = Field(default=0, description="Number of retries on failure")
    custom_parameters: Dict[str, Any] = Field(default_factory=dict, description="Custom parameters")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, description="Resource limits")
    logging_level: str = Field(default="INFO", description="Logging level")
    
    class Config:
        use_enum_values = True


class ToolCategoryConfig(BaseModel):
    """Configuration for tool categories."""
    
    category: str = Field(..., description="Category name")
    enabled: bool = Field(default=True, description="Whether category is enabled")
    max_concurrent_tools: int = Field(default=10, description="Maximum concurrent tools")
    default_timeout: int = Field(default=300, description="Default timeout for category")
    resource_pool: str = Field(default="default", description="Resource pool to use")
    
    class Config:
        use_enum_values = True


def create_tool_schema(
    name: str,
    description: str,
    category: str,
    parameters: Optional[List[Dict[str, Any]]] = None,
    returns: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ToolSchema:
    """Create a ToolSchema from basic parameters.
    
    Args:
        name: Tool name
        description: Tool description
        category: Tool category
        parameters: List of parameter definitions
        returns: Return value schema
        **kwargs: Additional schema properties
        
    Returns:
        ToolSchema instance
    """
    param_objects = []
    
    if parameters:
        for param in parameters:
            param_objects.append(ToolParameter(**param))
    
    return ToolSchema(
        name=name,
        description=description,
        category=category,
        parameters=param_objects,
        returns=returns or {"type": "object", "description": "Tool execution result"},
        **kwargs
    )
