"""
MCP Resource Schemas

Definitions for MCP resources, resource templates, access patterns,
and resource management operations following the Model Context Protocol specification.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
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
    mime_type: Optional[str] = Field(default=None, description="Resource MIME type")
    access: List[MCPResourceAccess] = Field(default_factory=list, description="Allowed access levels")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Resource metadata")
    tags: Optional[List[str]] = Field(default_factory=list, description="Resource tags")
    version: Optional[str] = Field(default="1.0.0", description="Resource version")
    deprecated: Optional[bool] = Field(default=False, description="Whether resource is deprecated")


class MCPResourceTemplate(BaseModel):
    """Template for creating resources with variable substitution."""
    name: str = Field(description="Template name")
    description: str = Field(description="Template description")
    resource_type: MCPResourceType = Field(description="Resource type")
    uri_template: str = Field(description="URI template with variable placeholders")
    parameters: Dict[str, str] = Field(description="Parameter descriptions")
    default_values: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Default parameter values")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Template metadata")


class MCPResourceResult(BaseModel):
    """Result of a resource operation."""
    success: bool = Field(description="Whether operation was successful")
    data: Optional[Any] = Field(default=None, description="Resource data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Result metadata")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code")
    execution_time: Optional[float] = Field(default=None, description="Execution time in milliseconds")
    
    @classmethod
    def success_result(cls, data: Any, execution_time: Optional[float] = None) -> "MCPResourceResult":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            execution_time=execution_time
        )
    
    @classmethod
    def error_result(cls, error: str, error_code: Optional[str] = None, execution_time: Optional[float] = None) -> "MCPResourceResult":
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
    last_accessed: Optional[str] = Field(default=None, description="Last access timestamp")
    size: Optional[int] = Field(default=None, description="Resource size in bytes")
    checksum: Optional[str] = Field(default=None, description="Resource checksum")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Resource metadata")


class MCPResourceList(BaseModel):
    """List of available MCP resources."""
    resources: List[MCPResource] = Field(default_factory=list, description="Available resources")
    total_count: int = Field(default=0, description="Total number of resources")
    resource_types: List[MCPResourceType] = Field(default_factory=list, description="Available resource types")
    
    def __init__(self, **data):
        super().__init__(**data)
        self.total_count = len(self.resources)
        self.resource_types = list(set(resource.definition.resource_type for resource in self.resources))


class MCPResourceRequest(BaseModel):
    """Request to access or manipulate a resource."""
    resource_uri: str = Field(description="Resource URI")
    operation: str = Field(description="Operation to perform (read, write, delete, etc.)")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Operation parameters")
    access_level: Optional[MCPResourceAccess] = Field(default=MCPResourceAccess.READ, description="Required access level")
    timeout: Optional[int] = Field(default=None, description="Operation timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Request metadata")


class MCPResourceResponse(BaseModel):
    """Response from a resource operation."""
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    resource_uri: str = Field(description="Resource URI")
    operation: str = Field(description="Performed operation")
    result: MCPResourceResult = Field(description="Operation result")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response metadata")


class MCPResourceSubscription(BaseModel):
    """Subscription to resource changes."""
    resource_uri: str = Field(description="Resource URI to subscribe to")
    subscription_id: str = Field(description="Unique subscription identifier")
    events: List[str] = Field(default_factory=list, description="Events to subscribe to")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Event filters")
    created_at: str = Field(description="Subscription creation timestamp")
    active: bool = Field(default=True, description="Whether subscription is active")


class MCPResourceEvent(BaseModel):
    """Resource change event."""
    resource_uri: str = Field(description="Resource URI")
    event_type: str = Field(description="Event type (created, updated, deleted, etc.)")
    timestamp: str = Field(description="Event timestamp")
    data: Optional[Any] = Field(default=None, description="Event data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Event metadata")
