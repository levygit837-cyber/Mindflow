from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from deepagents.backends.protocol import BackendProtocol
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.orchestration.orchestrator import AgentType

_logger = get_logger(__name__)

T = TypeVar("T")


class ToolRegistry:
    """Central registry for agent tools with scoped access per AgentType.

    This registry normalizes tools from various sources (deepagents, custom)
    and ensures they are invoked with consistent patterns (kwargs, Pydantic outputs).
    """

    def __init__(self, backend: BackendProtocol):
        self.backend = backend
        self._tools: dict[str, tuple[Callable, list[AgentType]]] = {}

    def register_tool(
        self,
        name: str,
        func: Callable,
        scopes: list[AgentType] | None = None,
    ) -> None:
        """Register a tool function with optional agent scopes.

        If scopes is None, the tool is available to all agents.
        """
        self._tools[name] = (func, scopes or list(AgentType))
        _logger.debug("tool_registered", name=name, scopes=str(scopes))

    def get_tools_for_agent(self, agent_type: AgentType) -> list[Callable]:
        """Return a list of tool functions authorized for the given agent type."""
        authorized_tools = []
        for name, (func, scopes) in self._tools.items():
            if agent_type in scopes:
                authorized_tools.append(func)
        return authorized_tools

    def get_all_tool_names(self) -> list[str]:
        """Return a list of all registered tool names."""
        return list(self._tools.keys())


def create_default_registry(backend: BackendProtocol) -> ToolRegistry:
    """Factory to create a ToolRegistry with standard deepagents tools integrated."""
    registry = ToolRegistry(backend)

    # 1. Integrate DeepAgents Filesystem Tools (L1-L2)
    # We wrap them to ensure keyword argument support and logging
    
    def ls_info_tool(path: str = ".") -> Any:
        return backend.ls_info(path)

    def read_tool(file_path: str, offset: int = 0, limit: int = 2000) -> str:
        return backend.read(file_path, offset=offset, limit=limit)

    def write_tool(file_path: str, content: str) -> Any:
        return backend.write(file_path, content)

    def edit_tool(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> Any:
        return backend.edit(file_path, old_string, new_string, replace_all=replace_all)

    def grep_tool(pattern: str, path: str | None = None, glob: str | None = None) -> Any:
        return backend.grep_raw(pattern, path=path, glob=glob)

    def glob_tool(pattern: str, path: str = "/") -> Any:
        return backend.glob_info(pattern, path=path)

    # Register FS tools for common use (will be scoped in _registry.py)
    registry.register_tool("ls_info", ls_info_tool)
    registry.register_tool("read_file", read_tool)
    registry.register_tool("write_file", write_tool)
    registry.register_tool("edit_file", edit_tool)
    registry.register_tool("grep_search", grep_tool)
    registry.register_tool("glob_search", glob_tool)

    return registry
