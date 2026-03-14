"""Tool invocation loop (ReAct pattern) for MindFlow agents.

Provides ``invoke_with_tools`` — an async helper that runs the LLM in a
tool-use loop:

1. Call LLM with bound tools.
2. If the response contains ``tool_calls``, execute each tool and append the
   results as ``ToolMessage`` entries.
3. Repeat until no more tool calls or ``max_iterations`` is reached.
4. Return the final text response.

This module is imported by ``orchestrator/graph.py`` (execute_node) and
``orchestrator/delegation/engine.py`` (delegate_task).
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Maximum number of tool-call → response cycles before forcing a stop.
DEFAULT_MAX_ITERATIONS = 6


async def invoke_with_tools(
    llm: Any,
    messages: list[dict | Any],
    lc_tools: list[Any],
    *,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    event_dispatcher: Callable[[str, dict], Awaitable[None]] | None = None,
) -> str:
    """Execute ``llm`` in a ReAct loop with ``lc_tools``.

    Args:
        llm: A LangChain chat model already bound to tools via ``bind_tools()``.
        messages: Initial messages list (system + user).
        lc_tools: List of LangChain ``StructuredTool`` objects (used for
            ``ainvoke`` by name).
        max_iterations: Hard cap on tool-call cycles.
        event_dispatcher: Optional async callable ``(event_name, payload)`` used
            to surface tool events into the LangGraph event stream.

    Returns:
        The final text response as a plain string.
    """
    from langchain_core.messages import ToolMessage

    tools_by_name: dict[str, Any] = {t.name: t for t in lc_tools}
    working_messages: list[Any] = list(messages)
    final_text: str = ""

    for iteration in range(max_iterations):
        _logger.debug(f"tool_loop iteration={iteration}, messages={len(working_messages)}")

        response = await llm.ainvoke(working_messages)

        # Collect tool calls from the response
        tool_calls: list[dict] = getattr(response, "tool_calls", []) or []

        if not tool_calls:
            # No tool calls → extract text and exit the loop.
            # Handles Gemini thinking model output where content is a list of
            # {type: "text"|"thinking", text|thinking: "..."} dicts.
            content = getattr(response, "content", "")
            if isinstance(content, str):
                final_text = content
            elif isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict):
                        if part.get("type") == "text":
                            parts.append(part.get("text", ""))
                final_text = "".join(parts)
            else:
                final_text = str(content) if content else ""

            # If still empty, try the MindFlow response parser as last resort
            if not final_text:
                try:
                    from mindflow_backend.runtime.utils.response_parser import extract_text_only
                    final_text = extract_text_only(response)
                except Exception as exc:
                    _logger.warning(f"extract_text_only failed: {exc}")
            break

        # Append the assistant message (with tool_calls) so the model sees its
        # own decision in the next turn.
        working_messages.append(response)

        # Execute each tool call and collect ToolMessage results
        for tool_call in tool_calls:
            tool_name: str = tool_call.get("name", "")
            tool_args: dict = tool_call.get("args", {})
            tool_call_id: str = tool_call.get("id", "")

            _logger.info(
                "tool_invoked",
                tool=tool_name,
                args=str(tool_args)[:200],
                iteration=iteration,
            )

            if tool_name in tools_by_name:
                try:
                    tool = tools_by_name[tool_name]
                    raw_result = await tool.ainvoke(tool_args)
                    tool_result_str = (
                        raw_result
                        if isinstance(raw_result, str)
                        else json.dumps(raw_result, ensure_ascii=False, default=str)
                    )
                except Exception as exc:
                    tool_result_str = json.dumps(
                        {"success": False, "error": f"Tool execution failed: {exc}"}
                    )
                    _logger.warning(f"tool_execution_error tool={tool_name} error={exc}")
            else:
                tool_result_str = json.dumps(
                    {"success": False, "error": f"Unknown tool: {tool_name}"}
                )
                _logger.warning(f"tool_not_found name={tool_name}")

            # Optionally surface the tool call to the streaming event system
            if event_dispatcher is not None:
                try:
                    await event_dispatcher(
                        "tool_call",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result_preview": tool_result_str[:300],
                        },
                    )
                except Exception:
                    pass  # Non-critical — don't crash the loop

            working_messages.append(
                ToolMessage(
                    content=tool_result_str,
                    tool_call_id=tool_call_id,
                )
            )

        _logger.info(
            "tool_loop_cycle_done",
            iteration=iteration,
            tool_calls=len(tool_calls),
        )

    if not final_text:
        # Safety fallback: extract content from last response if loop exhausted
        try:
            from mindflow_backend.runtime.utils.response_parser import extract_text_only
            last_resp = await llm.ainvoke(working_messages)
            final_text = extract_text_only(last_resp)
        except Exception as exc:
            _logger.error(f"tool_loop_fallback_failed: {exc}")

    return final_text


async def stream_with_tools(
    llm: Any,
    messages: list[dict | Any],
    lc_tools: list[Any],
    *,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    chunk_dispatcher: Callable[[str], Awaitable[None]] | None = None,
    event_dispatcher: Callable[[str, dict], Awaitable[None]] | None = None,
) -> str:
    """Like ``invoke_with_tools`` but streams the final LLM response.

    Tool execution rounds use ``ainvoke`` (no streaming needed for intermediate
    steps).  Only the final answer is streamed chunk-by-chunk via
    ``chunk_dispatcher``.

    Args:
        llm: LangChain chat model (already ``bind_tools``'d if tools are needed).
        messages: Initial messages list.
        lc_tools: LangChain tool list.
        max_iterations: Hard cap on tool-call cycles.
        chunk_dispatcher: Called with each text chunk of the final response.
        event_dispatcher: Called for tool-call events.

    Returns:
        The complete final text response.
    """
    from langchain_core.messages import ToolMessage
    from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts

    tools_by_name: dict[str, Any] = {t.name: t for t in lc_tools}
    working_messages: list[Any] = list(messages)
    full_response: list[str] = []

    # --- Tool call rounds (non-streaming) ---
    for iteration in range(max_iterations):
        response = await llm.ainvoke(working_messages)
        tool_calls: list[dict] = getattr(response, "tool_calls", []) or []

        if not tool_calls:
            # No tool calls — proceed to final streaming pass below
            break

        working_messages.append(response)

        for tool_call in tool_calls:
            tool_name: str = tool_call.get("name", "")
            tool_args: dict = tool_call.get("args", {})
            tool_call_id: str = tool_call.get("id", "")

            _logger.info("stream_tool_invoked", tool=tool_name, iteration=iteration)

            if tool_name in tools_by_name:
                try:
                    raw_result = await tools_by_name[tool_name].ainvoke(tool_args)
                    tool_result_str = (
                        raw_result
                        if isinstance(raw_result, str)
                        else json.dumps(raw_result, ensure_ascii=False, default=str)
                    )
                except Exception as exc:
                    tool_result_str = json.dumps({"success": False, "error": str(exc)})
            else:
                tool_result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})

            if event_dispatcher is not None:
                try:
                    await event_dispatcher(
                        "tool_call",
                        {"tool": tool_name, "args": tool_args, "result_preview": tool_result_str[:300]},
                    )
                except Exception:
                    pass

            working_messages.append(
                ToolMessage(content=tool_result_str, tool_call_id=tool_call_id)
            )

    # --- Final streaming pass ---
    async for chunk in llm.astream(working_messages):
        thought, texts = extract_chunk_parts(chunk)
        if thought and event_dispatcher:
            try:
                await event_dispatcher("agent_thought", {"thought": thought})
            except Exception:
                pass
        for text in texts:
            full_response.append(text)
            if chunk_dispatcher is not None:
                try:
                    await chunk_dispatcher(text)
                except Exception:
                    pass

    return "".join(full_response)
