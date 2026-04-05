"""Legacy compatibility module for deprecated tool execution functions.

.. deprecated::
    This module is deprecated and provides backward compatibility wrappers only.
    Use ``DelegationEngine`` or ``invoke_with_callable_tools`` for tool execution.
    This module will be removed in a future version.

IMPORTANT: The canonical execution path is now DelegationEngine. This module
exists only for backward compatibility during migration. All new code should use
DelegationEngine or invoke_with_callable_tools directly.

Functions:
- invoke_with_tools: ReAct pattern tool loop (non-streaming) - DEPRECATED
- stream_with_tools: ReAct pattern tool loop (streaming) - DEPRECATED
- ToolExecutionLoop: Unified tool execution loop class - DEPRECATED
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

# Re-export from archive (legacy modules moved to archive/)
# These functions have been migrated internally to use StreamingToolExecutor.execute_batch()
from mindflow_backend.archive.tool_invocation import (
    invoke_with_tools,
    stream_with_tools,
)
from mindflow_backend.archive.tool_loop import ToolExecutionLoop

__all__ = [
    "invoke_with_tools",
    "stream_with_tools",
    "ToolExecutionLoop",
]
