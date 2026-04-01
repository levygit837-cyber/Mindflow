"""Temporary adapter: CallableTool → LangChain StructuredTool.

This adapter provides backward compatibility during the migration from
LangChain-based tools to native callable tools. It converts CallableTool
instances to LangChain StructuredTool objects.

IMPORTANT: This is a TEMPORARY adapter for migration only. Once all tools
are migrated and the ReAct loop is updated to use callable tools directly,
this module should be DELETED.

Migration path:
1. Phase 1: Create callable infrastructure (this adapter)
2. Phase 2: Migrate tools to CallableTool
3. Phase 3: Update ReAct loop to use callable tools directly
4. Phase 4: DELETE this adapter

Example:
    # During migration - convert callable tool to LangChain
    callable_tool = build_callable_tool(...)
    lc_tool = callable_to_langchain(callable_tool)

    # After migration - use callable tool directly
    result = await callable_tool.call(input, context)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.callable import CallableTool
from mindflow_backend.schemas.tools.context import ToolContext

_logger = get_logger(__name__)


def callable_to_langchain(callable_tool: CallableTool) -> Any:
    """Convert CallableTool to LangChain StructuredTool.

    This is a TEMPORARY adapter for migration. It wraps a CallableTool
    in a LangChain StructuredTool interface so it can be used with
    existing LangChain-based code.

    Args:
        callable_tool: CallableTool instance to convert

    Returns:
        LangChain StructuredTool instance

    Example:
        file_read_tool = build_callable_tool(...)
        lc_tool = callable_to_langchain(file_read_tool)

        # Use with LangChain
        llm_with_tools = llm.bind_tools([lc_tool])
    """
    try:
        from langchain_core.tools import StructuredTool
    except ImportError:
        _logger.error("langchain_core not installed - cannot convert callable tools")
        raise ImportError(
            "langchain_core is required for callable_to_langchain adapter. "
            "Install with: pip install langchain-core"
        )

    # Get input schema (already a Pydantic model)
    input_schema = callable_tool.input_schema

    # Build metadata
    tool_metadata = {
        "tool_name": callable_tool.name,
        "tool_type": "callable",
        "is_read_only": callable_tool.is_read_only,
        "is_concurrency_safe": callable_tool.is_concurrency_safe,
        "is_destructive": callable_tool.is_destructive,
        "interrupt_behavior": callable_tool.interrupt_behavior(),
    }

    # Keep stable reference to avoid closure issues
    _tool = callable_tool

    async def _arun(**kwargs: Any) -> str:
        """Async execution wrapper that creates ToolContext and calls the tool."""
        try:
            # Create minimal context
            # TODO: Inject real permission_context from runtime
            context = ToolContext(
                permission_context=None,
                metadata={
                    "tool_name": _tool.name,
                    "tool_input": kwargs,
                    "adapter": "callable_to_langchain",
                },
            )

            # Validate input with Pydantic
            try:
                validated_input = input_schema(**kwargs)
            except Exception as e:
                _logger.warning(f"Input validation failed for {_tool.name}: {e}")
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Invalid input: {e}",
                        "error_code": "VALIDATION_ERROR",
                    }
                )

            # Execute tool
            result = await _tool.call(validated_input, context, on_progress=None)

            # Convert ToolResult to JSON string
            if result.success:
                # Return data directly if it's already a dict
                if isinstance(result.data, dict):
                    return json.dumps(result.data, ensure_ascii=False, default=str)
                # Wrap non-dict data
                return json.dumps(
                    {"success": True, "data": result.data, "metadata": result.metadata},
                    ensure_ascii=False,
                    default=str,
                )
            else:
                return json.dumps(
                    {
                        "success": False,
                        "error": result.error,
                        "metadata": result.metadata,
                    },
                    ensure_ascii=False,
                )

        except Exception as exc:
            _logger.error(f"Tool execution failed for {_tool.name}: {exc}", exc_info=True)
            return json.dumps(
                {
                    "success": False,
                    "error": str(exc),
                    "error_code": "EXECUTION_ERROR",
                }
            )

    def _run(**kwargs: Any) -> str:
        """Sync fallback - runs async call in event loop."""
        try:
            return asyncio.run(_arun(**kwargs))
        except Exception as exc:
            _logger.error(f"Sync execution failed for {_tool.name}: {exc}")
            return json.dumps({"success": False, "error": str(exc)})

    # Create LangChain StructuredTool
    lc_tool = StructuredTool.from_function(
        func=_run,
        coroutine=_arun,
        name=_tool.name,
        description=_tool.description,
        args_schema=input_schema,
        handle_tool_error=True,
        metadata=tool_metadata,
    )

    _logger.debug(f"Converted callable tool '{_tool.name}' → LangChain StructuredTool")
    return lc_tool


def callables_to_langchain(callable_tools: list[CallableTool]) -> list[Any]:
    """Convert multiple CallableTool instances to LangChain StructuredTools.

    This is a TEMPORARY adapter for migration. Converts a list of callable
    tools to LangChain format, deduplicating by name.

    Args:
        callable_tools: List of CallableTool instances

    Returns:
        List of LangChain StructuredTool instances

    Example:
        tools = [file_read_tool, file_write_tool, grep_tool]
        lc_tools = callables_to_langchain(tools)

        # Use with LangChain
        llm_with_tools = llm.bind_tools(lc_tools)
    """
    result = []
    seen_names: set[str] = set()

    for tool in callable_tools:
        tool_name = tool.name

        # Skip duplicates
        if tool_name in seen_names:
            _logger.debug(f"Skipping duplicate callable tool '{tool_name}'")
            continue

        # Convert to LangChain
        try:
            lc_tool = callable_to_langchain(tool)
            result.append(lc_tool)
            seen_names.add(tool_name)
        except Exception as exc:
            _logger.warning(f"Failed to convert callable tool '{tool_name}': {exc}")
            continue

    _logger.info(
        f"Converted {len(result)}/{len(callable_tools)} callable tools to LangChain format"
    )
    return result


# ── Hybrid Adapter: Mix Legacy + Callable Tools ──


def hybrid_tools_to_langchain(
    legacy_tools: list[Any],
    callable_tools: list[CallableTool],
) -> list[Any]:
    """Convert mix of legacy and callable tools to LangChain format.

    This adapter supports the migration period where some tools are still
    using the old AsyncToolInterface pattern and others have been migrated
    to CallableTool.

    Args:
        legacy_tools: List of AsyncToolInterface tools (old pattern)
        callable_tools: List of CallableTool instances (new pattern)

    Returns:
        List of LangChain StructuredTool instances (deduplicated)

    Example:
        # During migration - mix of old and new tools
        legacy = [old_http_client, old_web_scraper]
        callable = [new_file_read, new_file_write]

        all_lc_tools = hybrid_tools_to_langchain(legacy, callable)
        llm_with_tools = llm.bind_tools(all_lc_tools)
    """
    from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools

    # Convert legacy tools using existing adapter
    lc_legacy = to_langchain_tools(legacy_tools)

    # Convert callable tools using new adapter
    lc_callable = callables_to_langchain(callable_tools)

    # Combine and deduplicate by name
    result = []
    seen_names: set[str] = set()

    for tool in lc_legacy + lc_callable:
        tool_name = tool.name
        if tool_name not in seen_names:
            result.append(tool)
            seen_names.add(tool_name)
        else:
            _logger.debug(f"Skipping duplicate tool '{tool_name}' in hybrid conversion")

    _logger.info(
        f"Hybrid conversion: {len(lc_legacy)} legacy + {len(lc_callable)} callable "
        f"= {len(result)} total tools"
    )
    return result
