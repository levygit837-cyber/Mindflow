"""MindFlow tool schemas — standardized permission and execution system.

Mirrors the Claude Code CLI tool system:
- Tool[T_in, T_out]: Unified interface with explicit permission metadata
- ToolPermissionContext: Centralized rule evaluation (deny → allow → ask → mode)
- ToolExecutionMode: accepts_edits / ask / bypass (derived from tool metadata)
- build_tool(): Factory with safe defaults (fail-closed)

Migration from legacy schemas:
- ToolSchema → still exported, use tool.to_tool_schema() for conversion
- ToolParameterSchema → still exported, used by ToolSchema
- PermissionResult → now check_tool() → PermissionResult from context.py
"""

from __future__ import annotations

# -- Core interface (NEW — primary API going forward) --
from mindflow_backend.schemas.tools.tool import (
    Tool,
    ToolContext,
    tool,
    ToolBase,  # Backwards-compatible alias
)

# -- Factory (NEW — recommended way to create tools) --
from mindflow_backend.schemas.tools.builder import (
    build_tool,
    TOOL_DEFAULTS,
)

# -- Execution mode (NEW — defines how tools execute) --
from mindflow_backend.schemas.tools.execution import ToolExecutionMode

# -- Permission system (existing — enhanced with context.py) --
from mindflow_backend.schemas.tools.permission import (
    PermissionBehavior,
    PermissionMode,
    PermissionResult,
    PermissionRule,
    RuleSource,
)

# -- Permission context (NEW — aggregates rules) --
from mindflow_backend.schemas.tools.context import (
    ToolPermissionContext,
    sandbox_context,
    strict_context,
    read_only_context,
)

# -- Existing schemas (keep exporting for backwards compatibility) --
from mindflow_backend.schemas.tools.base import (
    make_parameter,
    make_tool_schema,
    ParameterType,
    ToolParameterSchema,
    ToolSchema,
)

from mindflow_backend.schemas.tools.registry import (
    get_registry,
    reset_registry,
    LazyToolRegistration,
    ToolRegistration,
    ToolRegistry,
)

# -- Progress, Result (existing) --
from mindflow_backend.schemas.tools.progress import ToolProgressData
from mindflow_backend.schemas.tools.result import (
    ToolResult,
    ValidationResult,
    ContentReplacement,
    ToolResultBudget,
    ResultTruncation,
)

__all__ = [
    # Primary API (new)
    "Tool",
    "ToolContext",
    "ToolBase",
    "tool",
    "build_tool",
    "TOOL_DEFAULTS",
    "ToolExecutionMode",
    "ToolPermissionContext",
    "sandbox_context",
    "strict_context",
    "read_only_context",
    # Permission system
    "PermissionBehavior",
    "PermissionMode",
    "PermissionResult",
    "PermissionRule",
    "RuleSource",
    # Existing schemas (backwards compatibility)
    "make_parameter",
    "make_tool_schema",
    "ParameterType",
    "ToolParameterSchema",
    "ToolSchema",
    "get_registry",
    "reset_registry",
    "LazyToolRegistration",
    "ToolRegistration",
    "ToolRegistry",
    # Progress and result types
    "ToolProgressData",
    "ToolResult",
    "ValidationResult",
    "ContentReplacement",
    "ToolResultBudget",
    "ResultTruncation",
]
