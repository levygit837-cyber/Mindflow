"""Backward-compatible shim — canonical location: omnimind_backend.runtime.stream"""

from omnimind_backend.runtime.stream import (  # noqa: F401
    SYSTEM_PROMPT,
    AgentRuntime,
)

__all__ = ["AgentRuntime", "SYSTEM_PROMPT"]
