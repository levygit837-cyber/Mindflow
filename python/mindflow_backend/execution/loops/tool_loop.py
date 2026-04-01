"""Tool execution loop - unified ReAct pattern implementation.

This module replaces the separate invoke_with_tools() and stream_with_tools()
functions with a single unified loop that supports both streaming and non-streaming
execution.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class ToolLoopResult:
    """Result from a tool execution loop."""

    final_response: str
    iterations: int
    tool_calls: list[dict[str, Any]]
    stopped_reason: str  # "no_tools" | "max_iterations" | "error"


class ToolExecutionLoop:
    """Unified tool execution loop implementing the ReAct pattern.

    This class replaces the separate invoke_with_tools() and stream_with_tools()
    functions with a single implementation that supports both modes.

    Features:
    - Streaming and non-streaming execution
    - Configurable iteration limits
    - Event dispatching for observability
    - Tool call tracking
    - Error handling and recovery
    """

    def __init__(
        self,
        max_iterations: int = 50,
        event_dispatcher: Callable[[str, dict], Awaitable[None]] | None = None,
        chunk_dispatcher: Callable[[str], Awaitable[None]] | None = None,
        before_iteration: Callable[[list[Any], int], Awaitable[None]] | None = None,
    ):
        """Initialize the tool loop.

        Args:
            max_iterations: Maximum number of tool-call rounds
            event_dispatcher: Called for tool events (name, payload)
            chunk_dispatcher: Called for streaming text chunks
            before_iteration: Called before each iteration (messages, iteration)
        """
        self.max_iterations = max_iterations
        self.event_dispatcher = event_dispatcher
        self.chunk_dispatcher = chunk_dispatcher
        self.before_iteration = before_iteration

    async def run(
        self,
        llm: Any,
        messages: list[Any],
        lc_tools: list[Any],
        stream: bool = False,
    ) -> ToolLoopResult:
        """Execute the tool loop.

        Args:
            llm: LangChain chat model (already bound to tools)
            messages: Initial messages list
            lc_tools: LangChain tool list
            stream: Whether to stream the final response

        Returns:
            ToolLoopResult with final response and metadata
        """
        if stream:
            return await self._run_streaming(llm, messages, lc_tools)
        else:
            return await self._run_non_streaming(llm, messages, lc_tools)

    async def _run_non_streaming(
        self,
        llm: Any,
        messages: list[Any],
        lc_tools: list[Any],
    ) -> ToolLoopResult:
        """Execute loop without streaming (invoke mode)."""
        from langchain_core.messages import ToolMessage

        tools_by_name: dict[str, Any] = {t.name: t for t in lc_tools}
        working_messages: list[Any] = list(messages)
        tool_calls_log: list[dict[str, Any]] = []
        iteration = 0

        while True:
            _logger.debug(f"tool_loop iteration={iteration}, messages={len(working_messages)}")

            # Pre-iteration hook
            if self.before_iteration is not None:
                await self.before_iteration(working_messages, iteration)

            # Call LLM
            response = await llm.ainvoke(working_messages)

            # Check for tool calls
            tool_calls: list[dict] = getattr(response, "tool_calls", []) or []

            if not tool_calls:
                # No more tools → extract final text
                from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts

                _, texts = extract_chunk_parts(response)
                final_text = "".join(texts)

                return ToolLoopResult(
                    final_response=final_text,
                    iterations=iteration,
                    tool_calls=tool_calls_log,
                    stopped_reason="no_tools",
                )

            # Execute tools
            working_messages.append(response)

            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", "")

                # Log tool call
                tool_calls_log.append({
                    "name": tool_name,
                    "args": tool_args,
                    "id": tool_id,
                    "iteration": iteration,
                })

                # Dispatch event
                if self.event_dispatcher:
                    await self.event_dispatcher("tool_call_start", {
                        "tool": tool_name,
                        "args": tool_args,
                        "tool_call_id": tool_id,
                    })

                # Execute tool
                tool = tools_by_name.get(tool_name)
                if tool is None:
                    result_str = f"Error: Tool '{tool_name}' not found"
                else:
                    try:
                        result = await tool.ainvoke(tool_args)
                        result_str = self._serialize_tool_result(result)
                    except Exception as exc:
                        result_str = f"Error executing {tool_name}: {exc}"
                        _logger.error(f"tool_execution_error tool={tool_name} error={exc}")

                # Dispatch result event
                if self.event_dispatcher:
                    await self.event_dispatcher("tool_call", {
                        "tool": tool_name,
                        "args": tool_args,
                        "tool_call_id": tool_id,
                        "result_preview": result_str[:200],
                    })

                # Add tool result to messages
                working_messages.append(
                    ToolMessage(content=result_str, tool_call_id=tool_id)
                )

            iteration += 1

            # Check iteration limit
            if iteration >= self.max_iterations:
                _logger.warning(f"tool_loop_max_iterations_reached max={self.max_iterations}")
                return ToolLoopResult(
                    final_response="Maximum iterations reached",
                    iterations=iteration,
                    tool_calls=tool_calls_log,
                    stopped_reason="max_iterations",
                )

    async def _run_streaming(
        self,
        llm: Any,
        messages: list[Any],
        lc_tools: list[Any],
    ) -> ToolLoopResult:
        """Execute loop with streaming (stream mode)."""
        from langchain_core.messages import ToolMessage
        from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts

        tools_by_name: dict[str, Any] = {t.name: t for t in lc_tools}
        working_messages: list[Any] = list(messages)
        tool_calls_log: list[dict[str, Any]] = []
        full_response: list[str] = []
        iteration = 0

        # Tool call rounds (non-streaming)
        while True:
            if self.before_iteration is not None:
                await self.before_iteration(working_messages, iteration)

            response = await llm.ainvoke(working_messages)
            tool_calls: list[dict] = getattr(response, "tool_calls", []) or []

            if not tool_calls:
                # No more tools → capture text and break to streaming phase
                _, texts = extract_chunk_parts(response)
                last_text = "".join(texts)
                if last_text.strip():
                    # We have a final answer already, stream it
                    if self.chunk_dispatcher:
                        await self.chunk_dispatcher(last_text)
                    full_response.append(last_text)
                    return ToolLoopResult(
                        final_response=last_text,
                        iterations=iteration,
                        tool_calls=tool_calls_log,
                        stopped_reason="no_tools",
                    )
                break

            # Execute tools (same as non-streaming)
            working_messages.append(response)

            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", "")

                tool_calls_log.append({
                    "name": tool_name,
                    "args": tool_args,
                    "id": tool_id,
                    "iteration": iteration,
                })

                if self.event_dispatcher:
                    await self.event_dispatcher("tool_call_start", {
                        "tool": tool_name,
                        "args": tool_args,
                        "tool_call_id": tool_id,
                    })

                tool = tools_by_name.get(tool_name)
                if tool is None:
                    result_str = f"Error: Tool '{tool_name}' not found"
                else:
                    try:
                        result = await tool.ainvoke(tool_args)
                        result_str = self._serialize_tool_result(result)
                    except Exception as exc:
                        result_str = f"Error executing {tool_name}: {exc}"

                if self.event_dispatcher:
                    await self.event_dispatcher("tool_call", {
                        "tool": tool_name,
                        "args": tool_args,
                        "tool_call_id": tool_id,
                        "result_preview": result_str[:200],
                    })

                working_messages.append(
                    ToolMessage(content=result_str, tool_call_id=tool_id)
                )

            iteration += 1

            if iteration >= self.max_iterations:
                return ToolLoopResult(
                    final_response="Maximum iterations reached",
                    iterations=iteration,
                    tool_calls=tool_calls_log,
                    stopped_reason="max_iterations",
                )

        # Final streaming phase
        async for chunk in llm.astream(working_messages):
            _, texts = extract_chunk_parts(chunk)
            for text in texts:
                if self.chunk_dispatcher:
                    await self.chunk_dispatcher(text)
                full_response.append(text)

        final_text = "".join(full_response)
        return ToolLoopResult(
            final_response=final_text,
            iterations=iteration,
            tool_calls=tool_calls_log,
            stopped_reason="no_tools",
        )

    @staticmethod
    def _serialize_tool_result(result: Any) -> str:
        """Serialize tool result to string."""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)
