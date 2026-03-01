"""Backward-compatible shim — canonical location: omnimind_backend.runtime.deep_agent_factory"""

from omnimind_backend.runtime.deep_agent_factory import (  # noqa: F401
    DeepAgentConfig,
    create_omnimind_deep_agent,
    search_web_tool,
)

__all__ = ["DeepAgentConfig", "create_omnimind_deep_agent", "search_web_tool"]
