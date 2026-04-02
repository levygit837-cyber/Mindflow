"""Helper to detect and separate callable vs legacy tools.

Provides utilities to identify which tools are CallableTools and which
are legacy AsyncToolInterface, enabling hybrid execution during Phase 3 migration.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def is_callable_tool(tool: Any) -> bool:
    """Check if a tool is a CallableTool instance.

    Args:
        tool: Tool instance to check

    Returns:
        True if tool is CallableTool, False otherwise
    """
    try:
        from mindflow_backend.schemas.tools import CallableTool
        return isinstance(tool, CallableTool)
    except ImportError:
        return False


def separate_tools(tools: list[Any]) -> tuple[list[Any], list[Any]]:
    """Separate tools into callable and legacy lists.

    Args:
        tools: Mixed list of CallableTool and legacy tool instances

    Returns:
        Tuple of (callable_tools, legacy_tools)
    """
    callable_tools = []
    legacy_tools = []

    for tool in tools:
        if is_callable_tool(tool):
            callable_tools.append(tool)
        else:
            legacy_tools.append(tool)

    return callable_tools, legacy_tools


def all_tools_are_callable(tools: list[Any]) -> bool:
    """Check if all tools in list are CallableTools.

    Args:
        tools: List of tool instances

    Returns:
        True if all tools are CallableTool instances
    """
    if not tools:
        return False

    return all(is_callable_tool(tool) for tool in tools)


def get_tool_execution_strategy(tools: list[Any]) -> str:
    """Determine which execution strategy to use based on tool types.

    Args:
        tools: List of tool instances

    Returns:
        "callable" - Use invoke_with_callable_tools (all tools are callable)
        "legacy" - Use invoke_with_tools (has legacy tools)
        "none" - No tools available
    """
    if not tools:
        return "none"

    callable_tools, legacy_tools = separate_tools(tools)

    if legacy_tools:
        # Has legacy tools → must use LangChain adapter
        _logger.debug(
            f"tool_execution_strategy=legacy "
            f"(callable={len(callable_tools)}, legacy={len(legacy_tools)})"
        )
        return "legacy"

    if callable_tools:
        # All tools are callable → use direct execution
        _logger.debug(f"tool_execution_strategy=callable (count={len(callable_tools)})")
        return "callable"

    return "none"
