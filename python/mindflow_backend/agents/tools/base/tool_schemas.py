"""
Tool schema definitions for MindFlow agents.

DEPRECATED: This module has been moved to mindflow_backend.schemas.tools.base
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.schemas.tools.base import ParameterType, ToolParameter, ToolSchema, ToolResult, create_tool_schema, create_parameter, validate_tool_parameters
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.schemas.tools.base import (
    ParameterType,
    ToolParameter,
    ToolResult,
    ToolSchema,
    create_parameter,
    create_tool_schema,
    validate_tool_parameters,
)

# Maintain backward compatibility
__all__ = [
    "ParameterType",
    "ToolParameter",
    "ToolSchema",
    "ToolResult",
    "create_tool_schema",
    "create_parameter",
    "validate_tool_parameters",
]
