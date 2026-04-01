"""
Tool schema definitions for MindFlow agents.

DEPRECATED: This module has been moved to mindflow_backend.schemas.tools
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.schemas.tools.base import ParameterType, ToolParameterSchema, ToolSchema, make_parameter, make_tool_schema
     from mindflow_backend.schemas.tools.result import ToolResult
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.schemas.tools.base import (
    ParameterType,
    ToolParameterSchema as ToolParameter,
    ToolSchema,
    make_parameter as create_parameter,
    make_tool_schema as create_tool_schema,
)
from mindflow_backend.schemas.tools.result import ToolResult

# Maintain backward compatibility
__all__ = [
    "ParameterType",
    "ToolParameter",
    "ToolSchema",
    "ToolResult",
    "create_tool_schema",
    "create_parameter",
]
