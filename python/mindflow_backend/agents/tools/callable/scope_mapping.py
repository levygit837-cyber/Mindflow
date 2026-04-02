"""Helper to map ToolScope to CallableTool instances.

Provides mapping from ToolScope enum to registered CallableTool instances,
replacing the legacy tool instantiation pattern.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.callable import (
    FileReadCallable,
    DirectoryListCallable,
    FileFinderCallable,
    GrepSearchCallable,
    GlobSearchCallable,
    FileWriteCallable,
    FileEditCallable,
    FileDeleteCallable,
    DirectoryCreateCallable,
    ShellExecutorCallable,
    SystemInfoCallable,
    ProcessManagerCallable,
    HttpClientCallable,
    WebScraperCallable,
    ApiClientCallable,
    TodoListReadCallable,
    TodoListWriteCallable,
    TodoListFocusCallable,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools import CallableTool

_logger = get_logger(__name__)


def get_callable_tools_for_scope(scope: Any) -> list[CallableTool]:
    """Get CallableTool instances for a given ToolScope.

    Args:
        scope: ToolScope enum value

    Returns:
        List of CallableTool instances for that scope
    """
    try:
        from mindflow_backend.schemas.orchestration.orchestrator import ToolScope

        if scope == ToolScope.FILESYSTEM:
            return [
                FileReadCallable,
                DirectoryListCallable,
                FileFinderCallable,
                GrepSearchCallable,
                GlobSearchCallable,
                FileWriteCallable,
                FileEditCallable,
                FileDeleteCallable,
                DirectoryCreateCallable,
            ]

        elif scope == ToolScope.SHELL:
            return [
                ShellExecutorCallable,
                SystemInfoCallable,
                ProcessManagerCallable,
            ]

        elif scope == ToolScope.WEB_SEARCH:
            return [
                HttpClientCallable,
                WebScraperCallable,
                ApiClientCallable,
            ]

        elif scope == ToolScope.PLANNING:
            return [
                TodoListReadCallable,
                TodoListWriteCallable,
                TodoListFocusCallable,
            ]

        elif scope == ToolScope.CODE_ANALYSIS:
            # CODE_ANALYSIS includes filesystem read-only tools
            return [
                FileReadCallable,
                DirectoryListCallable,
                FileFinderCallable,
                GrepSearchCallable,
                GlobSearchCallable,
            ]

        # Scopes not yet migrated to callable pattern
        elif scope in (
            ToolScope.BROWSER_SEARCH,
            ToolScope.PINCHTAB_FLEET,
            ToolScope.PINCHTAB_BROWSER,
            ToolScope.DATABASE,
            ToolScope.MEMORY,
            ToolScope.DELEGATION,
            ToolScope.ORCHESTRATION,
        ):
            _logger.debug(f"ToolScope {scope} not yet migrated to callable pattern")
            return []

        else:
            _logger.warning(f"Unknown ToolScope: {scope}")
            return []

    except ImportError as e:
        _logger.error(f"Failed to import ToolScope: {e}")
        return []


def get_all_callable_tools() -> list[CallableTool]:
    """Get all registered CallableTool instances.

    Returns:
        List of all 18 CallableTool instances
    """
    return [
        # Filesystem (9 tools)
        FileReadCallable,
        DirectoryListCallable,
        FileFinderCallable,
        GrepSearchCallable,
        GlobSearchCallable,
        FileWriteCallable,
        FileEditCallable,
        FileDeleteCallable,
        DirectoryCreateCallable,
        # System (3 tools)
        ShellExecutorCallable,
        SystemInfoCallable,
        ProcessManagerCallable,
        # Web (3 tools)
        HttpClientCallable,
        WebScraperCallable,
        ApiClientCallable,
        # Planning (3 tools)
        TodoListReadCallable,
        TodoListWriteCallable,
        TodoListFocusCallable,
    ]


def get_callable_tools_by_names(tool_names: list[str]) -> list[CallableTool]:
    """Get CallableTool instances by name.

    Args:
        tool_names: List of tool names to retrieve

    Returns:
        List of matching CallableTool instances
    """
    all_tools = get_all_callable_tools()
    tools_by_name = {t.name: t for t in all_tools}

    result = []
    for name in tool_names:
        if name in tools_by_name:
            result.append(tools_by_name[name])
        else:
            _logger.warning(f"CallableTool not found: {name}")

    return result
