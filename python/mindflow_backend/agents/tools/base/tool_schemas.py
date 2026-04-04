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
    ToolSchema,
)
from mindflow_backend.schemas.tools.base import (
    ToolParameterSchema as ToolParameter,
)
from mindflow_backend.schemas.tools.base import (
    make_parameter as create_parameter,
)
from mindflow_backend.schemas.tools.result import ToolResult
from mindflow_backend.schemas.tools.tool_config import (
    create_tool_schema as _create_tool_schema,
)


def create_tool_schema(*args, **kwargs):
    """Compatibility wrapper for legacy callers that still pass `returns=`.

    ``agents.tools`` still contains older compatibility layers that expect the
    higher-level schema builder from ``schemas.tools.tool_config`` instead of
    the lower-level ``make_tool_schema`` helper. Keep that behavior here so
    deprecated modules can remain loadable during the gradual migration.
    """
    return _create_tool_schema(*args, **kwargs)

# Maintain backward compatibility
__all__ = [
    "ParameterType",
    "ToolParameter",
    "ToolSchema",
    "ToolResult",
    "create_tool_schema",
    "create_parameter",
]
