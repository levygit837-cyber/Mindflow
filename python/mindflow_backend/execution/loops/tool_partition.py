"""Tool partition logic for Claude-style batch execution.

This module implements the partition logic from Claude Code's toolOrchestration.ts,
which groups consecutive concurrency-safe tools into parallel batches while
keeping non-concurrent tools in exclusive serial batches.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class ToolBatch:
    """A batch of tool calls to execute together.

    Attributes:
        is_concurrent_safe: Whether all tools in this batch can run concurrently
        blocks: List of tool call dictionaries
    """

    is_concurrent_safe: bool
    blocks: list[dict[str, Any]]


def partition_tool_calls(
    tool_calls: list[dict[str, Any]],
    tools_by_name: dict[str, Any],
) -> list[ToolBatch]:
    """Partition tool calls into concurrent-safe and serial batches.

    This implements the Claude Code pattern:
    - Consecutive concurrent-safe tools are grouped into parallel batches
    - Non-concurrent tools execute alone (exclusive access)
    - Final tool results are emitted in original tool-call order

    Args:
        tool_calls: List of tool call dictionaries with 'name' and 'args'
        tools_by_name: Dictionary mapping tool names to tool objects

    Returns:
        List of ToolBatch objects in execution order

    Example:
        >>> tool_calls = [
        ...     {"name": "file_read", "args": {"path": "a.txt"}},
        ...     {"name": "file_read", "args": {"path": "b.txt"}},
        ...     {"name": "file_write", "args": {"path": "c.txt"}},
        ... ]
        >>> tools = {"file_read": ReadOnlyTool(), "file_write": WriteTool()}
        >>> batches = partition_tool_calls(tool_calls, tools)
        >>> len(batches)
        2
        >>> batches[0].is_concurrent_safe  # Two file_reads can run together
        True
        >>> batches[1].is_concurrent_safe  # file_write runs alone
        False
    """
    batches: list[ToolBatch] = []
    current_safe_batch: list[dict[str, Any]] = []

    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        tool = tools_by_name.get(tool_name)

        # Determine if this tool is concurrent-safe
        is_concurrent_safe = _is_tool_concurrent_safe(tool, tool_call)

        if is_concurrent_safe:
            # Add to current concurrent-safe batch
            current_safe_batch.append(tool_call)
        else:
            # Flush current safe batch if exists
            if current_safe_batch:
                batches.append(ToolBatch(is_concurrent_safe=True, blocks=current_safe_batch))
                current_safe_batch = []
            
            # Create serial batch for non-concurrent tool
            batches.append(ToolBatch(is_concurrent_safe=False, blocks=[tool_call]))

    # Flush final safe batch
    if current_safe_batch:
        batches.append(ToolBatch(is_concurrent_safe=True, blocks=current_safe_batch))

    _logger.debug(
        "tool_partition_complete",
        total_tools=len(tool_calls),
        total_batches=len(batches),
        concurrent_batches=sum(1 for b in batches if b.is_concurrent_safe),
    )

    return batches


def _is_tool_concurrent_safe(
    tool: Any | None,
    tool_call: dict[str, Any],
) -> bool:
    """Check if a tool is safe for concurrent execution.

    Args:
        tool: The tool object (CallableTool or LangChain tool)
        tool_call: The tool call dictionary

    Returns:
        True if concurrent-safe, False otherwise
    """
    if tool is None:
        return False

    # Try CallableTool interface
    if hasattr(tool, "is_concurrency_safe"):
        try:
            # Check if it's a callable method or a boolean attribute
            concurrency_attr = getattr(tool, "is_concurrency_safe")
            if callable(concurrency_attr):
                # CallableTool.is_concurrency_safe() takes input parameter
                tool_args = tool_call.get("args", {})
                input_schema = getattr(tool, "input_schema", None)
                if input_schema:
                    try:
                        validated_input = input_schema(**tool_args)
                        return concurrency_attr(validated_input)
                    except Exception:
                        # If validation fails, assume not safe
                        return False
                else:
                    # Fallback: call without input
                    return concurrency_attr()
            else:
                # It's a boolean attribute (e.g., ToolDefinition)
                return bool(concurrency_attr)
        except Exception:
            return False

    # Try LangChain tool metadata
    tool_meta = _extract_tool_meta(tool)
    return bool(tool_meta and tool_meta.get("is_concurrency_safe", False))


def _extract_tool_meta(tool: Any | None) -> dict[str, Any] | None:
    """Extract tool metadata from various tool formats.

    Args:
        tool: The tool object

    Returns:
        Dictionary with tool metadata or None
    """
    if tool is None:
        return None

    # Try CallableTool.get_metadata()
    if hasattr(tool, "get_metadata"):
        try:
            return tool.get_metadata()
        except Exception:
            pass

    # Try LangChain metadata attribute
    tool_meta = getattr(tool, "metadata", None)
    if tool_meta is None:
        return None

    if isinstance(tool_meta, dict):
        return dict(tool_meta)

    try:
        return dict(tool_meta)
    except Exception:
        return {"value": str(tool_meta)}
