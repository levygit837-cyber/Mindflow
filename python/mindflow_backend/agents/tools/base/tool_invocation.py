"""Tool invocation loop (ReAct pattern) for MindFlow agents.

Provides ``invoke_with_tools`` — an async helper that runs the LLM in a
tool-use loop:

1. Call LLM with bound tools.
2. If the response contains ``tool_calls``, execute each tool and append the
   results as ``ToolMessage`` entries.
3. Repeat until the LLM produces no more tool calls (unlimited iterations).
4. Return the final text response.

This module is imported by ``graphs/implementations/orchestrator/simple_flow.py`` (execute_node) and
``orchestrator/delegation/engine.py`` (delegate_task).
"""

from __future__ import annotations

import json
import copy
from typing import Any, Awaitable, Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def _sanitize_tool_call_args(args: dict[str, Any]) -> dict[str, Any]:
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


async def invoke_with_tools(
    llm: Any,
    messages: list[dict | Any],
    lc_tools: list[Any],
    *,
    event_dispatcher: Callable[[str, dict], Awaitable[None]] | None = None,
    max_iterations: int = 50,
) -> str:
    """Execute ``llm`` in a ReAct loop with ``lc_tools``.

    The loop runs until the LLM stops issuing tool calls or ``max_iterations``
    is reached.

    Args:
        llm: A LangChain chat model already bound to tools via ``bind_tools()``.
        messages: Initial messages list (system + user).
        lc_tools: List of LangChain ``StructuredTool`` objects (used for
            ``ainvoke`` by name).
        event_dispatcher: Optional async callable ``(event_name, payload)`` used
            to surface tool events into the LangGraph event stream.
        max_iterations: Maximum number of tool-call rounds before forcing exit.

    Returns:
        The final text response as a plain string.
    """
    from langchain_core.messages import ToolMessage

    tools_by_name: dict[str, Any] = {t.name: t for t in lc_tools}
    working_messages: list[Any] = list(messages)
    final_text: str = ""
    iteration = 0

    while True:
        _logger.debug(f"tool_loop iteration={iteration}, messages={len(working_messages)}")

        response = await llm.ainvoke(working_messages)

        # Collect tool calls from the response
        tool_calls: list[dict] = getattr(response, "tool_calls", []) or []

        if not tool_calls:
            # No tool calls → extract text and exit the loop.
            # Use extract_chunk_parts which handles both plain dicts and Pydantic objects
            # (Gemini returns list content items as Pydantic objects, not plain dicts).
            from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts
            _, texts = extract_chunk_parts(response)
            final_text = "".join(texts)

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
        working_messages.append(_copy_response_with_sanitized_tool_calls(response, tool_calls))

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

            # Dispatch tool_call_start so the UI shows the tool as 'calling' immediately
            if event_dispatcher is not None:
                try:
                    tool_meta = getattr(tools_by_name.get(tool_name), "metadata", None)
                    await event_dispatcher(
                        "tool_call_start",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "tool_call_id": tool_call_id,
                            "tool_meta": tool_meta,
                        },
                    )
                except Exception:
                    pass

            if tool_name in tools_by_name:
                try:
                    tool = tools_by_name[tool_name]
                    tool_meta = getattr(tool, "metadata", None)
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
                tool_meta = None
                tool_result_str = json.dumps(
                    {"success": False, "error": f"Unknown tool: {tool_name}"}
                )
                _logger.warning(f"tool_not_found name={tool_name}")

            # Dispatch tool_call with result (tool_call_id included for matching in stream.py)
            if event_dispatcher is not None:
                try:
                    await event_dispatcher(
                        "tool_call",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result_preview": tool_result_str[:300],
                            "tool_call_id": tool_call_id,
                            "tool_meta": tool_meta,
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
        iteration += 1
        if iteration >= max_iterations:
            _logger.warning("tool_loop_max_iterations_reached", limit=max_iterations)
            break

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
    chunk_dispatcher: Callable[[str], Awaitable[None]] | None = None,
    event_dispatcher: Callable[[str, dict], Awaitable[None]] | None = None,
    max_iterations: int = 50,
) -> str:
    """Like ``invoke_with_tools`` but streams the final LLM response.

    Tool execution rounds use ``ainvoke`` (no streaming needed for intermediate
    steps).  Only the final answer is streamed chunk-by-chunk via
    ``chunk_dispatcher``.  The loop runs until the LLM stops issuing tool
    calls or ``max_iterations`` is reached.

    Args:
        llm: LangChain chat model (already ``bind_tools``'d if tools are needed).
        messages: Initial messages list.
        lc_tools: LangChain tool list.
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
    last_text_response: str = ""
    iteration = 0

    while True:
        response = await llm.ainvoke(working_messages)
        tool_calls: list[dict] = getattr(response, "tool_calls", []) or []

        if not tool_calls:
            # The LLM produced a text answer — capture it directly here instead of
            # discarding it and making a redundant second LLM call (which would still
            # have tools bound and could produce more tool calls instead of text).
            # Use extract_chunk_parts which handles both plain dicts and Pydantic objects
            # (Gemini returns list content items as Pydantic objects, not plain dicts).
            _, texts = extract_chunk_parts(response)
            last_text_response = "".join(texts)
            break

        working_messages.append(_copy_response_with_sanitized_tool_calls(response, tool_calls))

        for tool_call in tool_calls:
            tool_name: str = tool_call.get("name", "")
            tool_args: dict = tool_call.get("args", {})
            tool_call_id: str = tool_call.get("id", "")

            _logger.info("stream_tool_invoked", tool=tool_name, iteration=iteration)

            # Notify UI that tool is starting (shows 'calling' state immediately)
            if event_dispatcher is not None:
                try:
                    tool_meta = getattr(tools_by_name.get(tool_name), "metadata", None)
                    await event_dispatcher(
                        "tool_call_start",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "tool_call_id": tool_call_id,
                            "tool_meta": tool_meta,
                        },
                    )
                except Exception:
                    pass

            if tool_name in tools_by_name:
                try:
                    tool = tools_by_name[tool_name]
                    tool_meta = getattr(tool, "metadata", None)
                    raw_result = await tool.ainvoke(tool_args)
                    tool_result_str = (
                        raw_result
                        if isinstance(raw_result, str)
                        else json.dumps(raw_result, ensure_ascii=False, default=str)
                    )
                except Exception as exc:
                    tool_result_str = json.dumps({"success": False, "error": str(exc)})
            else:
                tool_meta = None
                tool_result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})

            # Notify UI that tool completed (shows result)
            if event_dispatcher is not None:
                try:
                    await event_dispatcher(
                        "tool_call",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result_preview": tool_result_str[:300],
                            "tool_call_id": tool_call_id,
                            "tool_meta": tool_meta,
                        },
                    )
                except Exception:
                    pass

            working_messages.append(
                ToolMessage(content=tool_result_str, tool_call_id=tool_call_id)
            )

        iteration += 1
        if iteration >= max_iterations:
            _logger.warning("stream_tool_loop_max_iterations_reached", limit=max_iterations)
            break

    # --- Dispatch captured text response or fall back to a fresh stream ---
    if last_text_response.strip():
        # Use the text the LLM already produced during the tool loop — no extra LLM call.
        full_response.append(last_text_response)
        if chunk_dispatcher is not None:
            try:
                await chunk_dispatcher(last_text_response)
            except Exception:
                pass
    else:
        # Fallback: loop exited without capturing a text answer.
        # Make one more streaming call (without bound tools if possible).
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
