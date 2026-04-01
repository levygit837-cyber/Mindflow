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
    tool,
    ToolBase,  # Backwards-compatible alias
)

# -- Tool Context (imported from context.py, not tool.py) --
from mindflow_backend.schemas.tools.context import ToolContext

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

# -- Streaming types (NEW — for StreamingToolExecutor) --
from mindflow_backend.schemas.tools.streaming_types import (
    ToolStatus,
    TrackedTool,
    StreamingToolResult,
    AbortController,
    ToolExecutionAbortedError,
    create_child_abort_controller,
)

# -- Callable tool infrastructure (PHASE 1 — eliminates LangChain dependency) --
from mindflow_backend.schemas.tools.callable import (
    CallableTool,
    ProgressCallback,
    ToolResult as CallableToolResult,  # Alias to avoid conflict with existing ToolResult
)

from mindflow_backend.schemas.tools.callable_builder import (
    CALLABLE_TOOL_DEFAULTS,
    build_callable_tool,
    build_readonly_tool,
    build_destructive_tool,
)

from mindflow_backend.schemas.tools.callable_executor import (
    StreamingToolExecutor,
    ToolExecutionState,
)

# Temporary adapter (will be removed in Phase 3)
from mindflow_backend.schemas.tools.callable_adapter import (
    callable_to_langchain,
    callables_to_langchain,
    hybrid_tools_to_langchain,
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
    # Streaming types (new)
    "ToolStatus",
    "TrackedTool",
    "StreamingToolResult",
    "AbortController",
    "ToolExecutionAbortedError",
    "create_child_abort_controller",
    # Callable tool infrastructure (Phase 1)
    "CallableTool",
    "CallableToolResult",
    "ProgressCallback",
    "build_callable_tool",
    "build_readonly_tool",
    "build_destructive_tool",
    "CALLABLE_TOOL_DEFAULTS",
    "StreamingToolExecutor",
    "ToolExecutionState",
    # Temporary adapter (Phase 1-2 only)
    "callable_to_langchain",
    "callables_to_langchain",
    "hybrid_tools_to_langchain",
]
