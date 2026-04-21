"""Canonical runtime compatibility shim.

The streaming runtime shell is the only supported public ``AgentRuntime``.
This module remains only to preserve legacy import paths while pointing every
caller at the canonical implementation.
"""

from __future__ import annotations

from mindflow_backend.runtime.streaming.stream import AgentRuntime as StreamingAgentRuntime


class AgentRuntime(StreamingAgentRuntime):
    """Backward-compatible alias for the canonical streaming runtime."""

    pass

