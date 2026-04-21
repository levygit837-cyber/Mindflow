"""Execution loops — compatibility re-exports.

Canonical location for StreamingToolExecutor / partition_tool_calls is now
``mindflow_backend.runtime.execution``. This package keeps re-exports so
existing callers continue to work during the unified-engine migration.

``tool_orchestration`` was removed in Phase 6 (dead code, zero production callers).
"""

from mindflow_backend.runtime.execution.streaming_executor import (
    StreamingToolExecutor,
    ToolDefinition,
    ToolUseContext,
)
from mindflow_backend.runtime.execution.tool_partition import (
    ToolBatch,
    partition_tool_calls,
)

__all__ = [
    "StreamingToolExecutor",
    "ToolDefinition",
    "ToolUseContext",
    "partition_tool_calls",
    "ToolBatch",
]
