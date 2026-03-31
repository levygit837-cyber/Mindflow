"""
MCP Resources Schemas

Schema definitions for MCP resources, including resource definitions,
templates, access patterns, and resource management operations.
"""

from .resource import (
    MCPResource,
    MCPResourceAccess,
    MCPResourceDefinition,
    MCPResourceResult,
    MCPResourceTemplate,
)

__all__ = [
    "MCPResource",
    "MCPResourceDefinition",
    "MCPResourceResult",
    "MCPResourceTemplate",
    "MCPResourceAccess",
]
