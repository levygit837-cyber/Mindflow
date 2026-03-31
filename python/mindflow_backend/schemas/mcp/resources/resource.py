"""
MCP Resource Schemas

Definitions for MCP resources, resource templates, access patterns,
and resource management operations following the Model Context Protocol specification.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MCPResourceType(str, Enum):
    """Supported resource types."""
    FILE = "file"
    DIRECTORY = "directory"
    DATABASE = "database"
    API = "api"
    STREAM = "stream"
    CUSTOM = "custom"


class MCPResourceAccess(str, Enum):
    """Resource access levels."""
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"
    EXECUTE = "execute"
    ADMIN = "admin"


class MCPResourceDefinition(BaseModel):
    """Definition of an MCP resource."""
    name: str = Field(description="Resource name")
    description: str = Field(description="Resource description")
    resource_type: MCPResourceType = Field(description="Resource type")
    uri: str = Field(description="Resource URI or identifier")
    mime_type: str | None = Field(default=None, description="Resource MIME type")
    access: list[MCPResourceAccess] = Field(default_factory=list, description="Allowed access levels")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Resource metadata")
    tags: list[str] | None = Field(default_factory=list, description="Resource tags")
    version: str | None = Field(default="1.0.0", description="Resource version")
    deprecated: bool | None = Field(default=False, description="Whether resource is deprecated")


class MCPResourceTemplate(BaseModel):
    """Template for creating resources with variable substitution."""
    name: str = Field(description="Template name")
    description: str = Field(description="Template description")
    resource_type: MCPResourceType = Field(description="Resource type")
    uri_template: str = Field(description="URI template with variable placeholders")
    parameters: dict[str, str] = Field(description="Parameter descriptions")
    default_values: dict[str, Any] | None = Field(default_factory=dict, description="Default parameter values")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Template metadata")


class MCPResourceResult(BaseModel):
    """Result of a resource operation."""
    success: bool = Field(description="Whether operation was successful")
    data: Any | None = Field(default=None, description="Resource data")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Result metadata")
    error: str | None = Field(default=None, description="Error message if failed")
    error_code: str | None = Field(default=None, description="Error code")
    execution_time: float | None = Field(default=None, description="Execution time in milliseconds")
    
    @classmethod
    def success_result(cls, data: Any, execution_time: float | None = None) -> "MCPResourceResult":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            execution_time=execution_time
        )
    
    @classmethod
    def error_result(cls, error: str, error_code: str | None = None, execution_time: float | None = None) -> "MCPResourceResult":
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            error_code=error_code,
            execution_time=execution_time
        )


class MCPResource(BaseModel):
    """Complete MCP resource with definition and state."""
    definition: MCPResourceDefinition = Field(description="Resource definition")
    enabled: bool = Field(default=True, description="Whether resource is enabled")
    access_count: int = Field(default=0, description="Number of times resource was accessed")
    last_accessed: str | None = Field(default=None, description="Last access timestamp")
    size: int | None = Field(default=None, description="Resource size in bytes")
    checksum: str | None = Field(default=None, description="Resource checksum")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Resource metadata")


class MCPResourceList(BaseModel):
    """List of available MCP resources."""
    resources: list[MCPResource] = Field(default_factory=list, description="Available resources")
    total_count: int = Field(default=0, description="Total number of resources")
    resource_types: list[MCPResourceType] = Field(default_factory=list, description="Available resource types")
    
    def __init__(self, **data):
        super().__init__(**data)
        self.total_count = len(self.resources)
        self.resource_types = list(set(resource.definition.resource_type for resource in self.resources))


class MCPResourceRequest(BaseModel):
    """Request to access or manipulate a resource."""
    resource_uri: str = Field(description="Resource URI")
    operation: str = Field(description="Operation to perform (read, write, delete, etc.)")
    parameters: dict[str, Any] | None = Field(default_factory=dict, description="Operation parameters")
    access_level: MCPResourceAccess | None = Field(default=MCPResourceAccess.READ, description="Required access level")
    timeout: int | None = Field(default=None, description="Operation timeout in seconds")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Request metadata")


class MCPResourceResponse(BaseModel):
    """Response from a resource operation."""
    request_id: str | None = Field(default=None, description="Request identifier")
    resource_uri: str = Field(description="Resource URI")
    operation: str = Field(description="Performed operation")
    result: MCPResourceResult = Field(description="Operation result")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Response metadata")


class MCPResourceSubscription(BaseModel):
    """Subscription to resource changes."""
    resource_uri: str = Field(description="Resource URI to subscribe to")
    subscription_id: str = Field(description="Unique subscription identifier")
    events: list[str] = Field(default_factory=list, description="Events to subscribe to")
    filters: dict[str, Any] | None = Field(default_factory=dict, description="Event filters")
    created_at: str = Field(description="Subscription creation timestamp")
    active: bool = Field(default=True, description="Whether subscription is active")


class MCPResourceEvent(BaseModel):
    """Resource change event."""
    resource_uri: str = Field(description="Resource URI")
    event_type: str = Field(description="Event type (created, updated, deleted, etc.)")
    timestamp: str = Field(description="Event timestamp")
    data: Any | None = Field(default=None, description="Event data")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Event metadata")
