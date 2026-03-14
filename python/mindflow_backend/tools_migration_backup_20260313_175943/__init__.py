"""Enhanced tool system for MindFlow agents.

Provides modular, extensible tool architecture with:
- Abstract interfaces for consistent tool behavior
- Enhanced registry with granular permissions
- Comprehensive validation and error handling
- Auto-discovery and caching capabilities
- Backward compatibility with existing tools
"""

from __future__ import annotations

from typing import Any

# Keep this module import-lightweight. Tool modules may depend on optional
# packages (browser/DB/redis). Import them lazily where needed.

from .base.tool_registry import ToolRegistry  # noqa: F401
from .base.tool_schemas import ToolSchema  # noqa: F401
from .sandbox import MindFlowSandbox  # noqa: F401


class _DefaultRegistry:
    """Minimal registry API used by orchestration code.

    Full tool authorization is implemented elsewhere; for unit tests and
    minimal runtime environments, returning an empty tool list is valid.
    """

    def __init__(self, sandbox: MindFlowSandbox) -> None:
        self.sandbox = sandbox

    def get_tools_for_agent(self, _agent_type: Any) -> list[Any]:
        return []


def create_default_registry(sandbox: MindFlowSandbox) -> _DefaultRegistry:
    """Create a default tool registry for an agent sandbox."""
    return _DefaultRegistry(sandbox)

__all__ = [
    # Core components
    "ToolRegistry",
    "ToolSchema",
    "MindFlowSandbox",
    "create_default_registry",
]
