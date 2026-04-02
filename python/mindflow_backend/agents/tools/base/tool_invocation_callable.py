"""Tool invocation loop using CallableTool pattern (Phase 3).

Provides direct tool execution without LangChain wrappers:
1. Call LLM with tool schemas (Pydantic models)
2. Parse tool calls from response
3. Execute CallableTool.call() directly
4. Append results and repeat until no more tool calls

This replaces tool_invocation.py's LangChain-based loop with native callable execution.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Awaitable, Callable
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools import CallableTool
from mindflow_backend.schemas.tools.context import ToolContext

_logger = get_logger(__name__)


def _sanitize_tool_call_args(args: dict[str, Any]) -> dict[str, Any]:
    """Sanitize tool call arguments for logging (same as legacy version)."""
    sanitized: dict[str, Any] = {}
    for key, value in args.items():
        if key == "content" and isinstance(value, str):
            first_line = value.splitlines()[0][:80] if value else ""
            sanitized[key] = (
                f"<omitted file content: {len(value)} chars; "
                f"re-read the file if you need to inspect it; first_line={first_line!r}>"
            )
            continue
        if isinstance(value, str) and len(value) > 240:
            sanitized[key] = f"<omitted long string: {len(value)} chars>"
            continue
        sanitized[key] = value
    return sanitized


def _copy_response_with_sanitized_tool_calls(response: Any, tool_calls: list[dict[str, Any]]) -> Any:
    """Create a copy of response with sanitized tool call arguments."""
    sanitized_tool_calls = []
    for tool_call in tool_calls:
        cloned = dict(tool_call)
        cloned["args"] = _sanitize_tool_call_args(tool_call.get("args", {}))
        sanitized_tool_calls.append(cloned)

    try:
        sanitized_response = response.model_copy(deep=True)
    except AttributeError:
        sanitized_response = copy.deepcopy(response)

    try:
        sanitized_response.tool_calls = sanitized_tool_calls
    except Exception:
        return response
    return sanitized_response


def _tool_schemas_for_llm(tools: list[CallableTool]) -> list[dict[str, Any]]:
    """Convert CallableTools to LLM-compatible tool schemas.

    Returns list of tool definitions with name, description, and parameters schema.
    """
    schemas = []
    for tool in tools:
        try:
            # Get Pydantic JSON schema from input_schema
            params_schema = tool.input_schema.model_json_schema()

            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": params_schema,
                }
            })
        except Exception as e:
            _logger.warning(f"Failed to generate schema for tool {tool.name}: {e}")

    return schemas


async def invoke_with_callable_tools(
    llm: Any,
    messages: list[dict | Any],
    callable_tools: list[CallableTool],
    tool_context: ToolContext,
    *,
    event_dispatcher: Callable[[str, dict], Awaitable[None]] | None = None,
    before_iteration: Callable[[list[Any], int], Awaitable[None]] | None = None,
    max_iterations: int = 50,
) -> str:
    """Execute LLM in a ReAct loop with CallableTools (no LangChain).

    Args:
        llm: LangChain chat model (will be bound to tools via bind_tools)
        messages: Initial messages list (system + user)
        callable_tools: List of CallableTool instances
        tool_context: ToolContext for tool execution (permissions, sandbox, etc.)
        event_dispatcher: Optional async callable (event_name, payload)
        before_iteration: Optional callback before each iteration
        max_iterations: Maximum tool-call rounds before exit

    Returns:
        Final text response as plain string
    """
    from langchain_core.messages import ToolMessage

    # Build tool lookup by name
    tools_by_name: dict[str, CallableTool] = {t.name: t for t in callable_tools}

    # Convert CallableTools to LLM tool schemas
    tool_schemas = _tool_schemas_for_llm(callable_tools)

    # Bind tools to LLM (LangChain still handles the LLM API call)
    llm_with_tools = llm.bind_tools(tool_schemas)

    working_messages: list[Any] = list(messages)
    final_text: str = ""
    iteration = 0

    while iteration < max_iterations:
        _logger.debug(f"callable_tool_loop iteration={iteration}, messages={len(working_messages)}")

        if before_iteration is not None:
            await before_iteration(working_messages, iteration)

        # Call LLM with bound tools
        response = await llm_with_tools.ainvoke(working_messages)

        # Extract tool calls from response
        tool_calls: list[dict] = getattr(response, "tool_calls", []) or []

        if not tool_calls:
            # No tool calls → extract text and exit
            from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts
            _, texts = extract_chunk_parts(response)
            final_text = "".join(texts)

            # Fallback to response parser if empty
            if not final_text:
                try:
                    from mindflow_backend.runtime.utils.response_parser import extract_text_only
                    final_text = extract_text_only(response)
                except Exception as exc:
                    _logger.warning(f"extract_text_only failed: {exc}")
            break

        # Append assistant message with tool calls
        working_messages.append(_copy_response_with_sanitized_tool_calls(response, tool_calls))

        # Execute each tool call using CallableTool.call()
        for tool_call in tool_calls:
            tool_name: str = tool_call.get("name", "")
            tool_args: dict = tool_call.get("args", {})
            tool_call_id: str = tool_call.get("id", "")

            _logger.info(
                "callable_tool_invoked",
                tool=tool_name,
                args=str(tool_args)[:200],
                iteration=iteration,
            )

            # Dispatch tool_call_start event
            if event_dispatcher is not None:
                try:
                    await event_dispatcher(
                        "tool_call_start",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "tool_call_id": tool_call_id,
                        },
                    )
                except Exception:
                    pass

            # Execute CallableTool directly
            if tool_name in tools_by_name:
                try:
                    tool = tools_by_name[tool_name]

                    # Validate and parse input using Pydantic
                    input_instance = tool.input_schema(**tool_args)

                    # Call tool directly (no LangChain wrapper)
                    result = await tool.call(input_instance, tool_context, on_progress=None)

                    # Convert ToolResult to JSON string
                    if result.success:
                        tool_result_str = json.dumps(
                            result.data if result.data is not None else {"success": True},
                            ensure_ascii=False,
                            default=str
                        )
                    else:
                        tool_result_str = json.dumps(
                            {"success": False, "error": result.error},
                            ensure_ascii=False
                        )

                except Exception as exc:
                    tool_result_str = json.dumps(
                        {"success": False, "error": f"Tool execution failed: {exc}"}
                    )
                    _logger.warning(f"callable_tool_execution_error tool={tool_name} error={exc}")
            else:
                tool_result_str = json.dumps(
                    {"success": False, "error": f"Unknown tool: {tool_name}"}
                )
                _logger.warning(f"callable_tool_not_found name={tool_name}")

            # Dispatch tool_call event with result
            if event_dispatcher is not None:
                try:
                    await event_dispatcher(
                        "tool_call",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result_preview": tool_result_str[:300],
                            "tool_call_id": tool_call_id,
                        },
                    )
                except Exception:
                    pass

            # Append ToolMessage with result
            working_messages.append(
                ToolMessage(
                    content=tool_result_str,
                    tool_call_id=tool_call_id,
                )
            )

        iteration += 1

    if iteration >= max_iterations:
        _logger.warning(f"callable_tool_loop_max_iterations_reached iterations={iteration}")

    return final_text
