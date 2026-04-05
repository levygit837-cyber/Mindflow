"""[DEPRECATED] Streaming tool executor with concurrency control.

.. deprecated::
    This module is deprecated. Use ``mindflow_backend.runtime.execution.streaming_executor``
    instead, which is the canonical StreamingToolExecutor with:
    - Pre/Post tool hooks integration
    - AbortController hierarchy
    - TrackedTool state management
    - Semaphore-based concurrency control
    - HookEventBroadcaster integration

This module will be removed in a future version.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "schemas.tools.callable_executor is deprecated. "
    "Use runtime.execution.streaming_executor instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2,
)


# Re-export for backward compatibility
# Import from canonical location
from mindflow_backend.runtime.execution.streaming_executor import (
    StreamingToolExecutor,
    ToolExecutionState,
)

__all__ = ["StreamingToolExecutor", "ToolExecutionState"]
