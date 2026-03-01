"""Backward-compatible shim — canonical location: omnimind_backend.runtime.log_bus"""

from omnimind_backend.runtime.log_bus import AgentLogBus, log_bus  # noqa: F401

__all__ = ["AgentLogBus", "log_bus"]
