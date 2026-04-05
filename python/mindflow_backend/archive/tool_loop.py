"""Tool execution loop - unified tool execution loop for MindFlow.

.. deprecated::
    This module is deprecated. Use ``mindflow_backend.runtime.execution.streaming_executor``
    (StreamingToolExecutor.execute_batch) for tool execution. This module will be removed
    in a future version.

This module replaces the separate invoke_with_tools() and stream_with_tools()
with a single unified loop that supports both streaming and non-streaming modes.

The loop:
1. Calls LLM with bound tools
2. Executes tool calls via StreamingToolExecutor
3. Feeds results back to LLM
4. Repeats until no more tool calls
"""

from __future__ import annotations

import json
import warnings
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

warnings.warn(
    "tool_loop module is deprecated. "
    "Use mindflow_backend.runtime.execution.streaming_executor.StreamingToolExecutor instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2,
)


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
        session_id: str | None = None,
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
        self.session_id = session_id

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

            # Execute tools using StreamingToolExecutor (unified executor)
            from mindflow_backend.runtime.execution.streaming_executor import (
                StreamingToolExecutor,
                ToolDefinition,
                ToolUseContext,
            )

            # Convert LangChain tools to ToolDefinitions
            tool_definitions: dict[str, ToolDefinition] = {}
            for tool in lc_tools:
                tool_name = getattr(tool, "name", "")
                if tool_name:
                    tool_definitions[tool_name] = ToolDefinition(
                        name=tool_name,
                        callable=tool.ainvoke,
                        is_concurrency_safe=getattr(tool, "is_concurrency_safe", True),
                        description=getattr(tool, "description", ""),
                    )

            # Create ToolUseContext
            tool_use_context = ToolUseContext(
                session_id=self.session_id or "unknown",
            )

            # Create can_use_tool function
            async def can_use_tool(tool_name: str, tool_input: dict[str, Any]) -> tuple[bool, str | None]:
                return (True, None)

            # Execute tool calls using StreamingToolExecutor
            executor = StreamingToolExecutor(
                tool_definitions=tool_definitions,
                can_use_tool=can_use_tool,
                tool_use_context=tool_use_context,
                max_concurrent=5,
            )

            # Convert tool_calls to the format expected by execute_batch
            batch_tool_calls = []
            for tc in tool_calls:
                batch_tool_calls.append({
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                    "id": tc.get("id", ""),
                })

            # Execute batch
            streaming_results = await executor.execute_batch(batch_tool_calls)

            # Convert StreamingToolResult to the format expected by the loop
            for result in streaming_results:
                if result.result:
                    serialized = result.result.to_dict() if hasattr(result.result, "to_dict") else str(result.result)
                else:
                    serialized = json.dumps({"success": False, "error": result.error}) if result.error else "{}"

                working_messages.append(
                    ToolMessage(
                        content=serialized,
                        tool_call_id=result.tool_id,
                    )
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

            # Execute tools using StreamingToolExecutor (unified executor)
            from mindflow_backend.runtime.execution.streaming_executor import (
                StreamingToolExecutor,
                ToolDefinition,
                ToolUseContext,
            )

            # Convert LangChain tools to ToolDefinitions
            tool_definitions: dict[str, ToolDefinition] = {}
            for tool in lc_tools:
                tool_name = getattr(tool, "name", "")
                if tool_name:
                    tool_definitions[tool_name] = ToolDefinition(
                        name=tool_name,
                        callable=tool.ainvoke,
                        is_concurrency_safe=getattr(tool, "is_concurrency_safe", True),
                        description=getattr(tool, "description", ""),
                    )

            # Create ToolUseContext
            tool_use_context = ToolUseContext(
                session_id=self.session_id or "unknown",
            )

            # Create can_use_tool function
            async def can_use_tool(tool_name: str, tool_input: dict[str, Any]) -> tuple[bool, str | None]:
                return (True, None)

            # Execute tool calls using StreamingToolExecutor
            executor = StreamingToolExecutor(
                tool_definitions=tool_definitions,
                can_use_tool=can_use_tool,
                tool_use_context=tool_use_context,
                max_concurrent=5,
            )

            # Convert tool_calls to the format expected by execute_batch
            batch_tool_calls = []
            for tc in tool_calls:
                batch_tool_calls.append({
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                    "id": tc.get("id", ""),
                })

            # Execute batch
            streaming_results = await executor.execute_batch(batch_tool_calls)

            # Convert StreamingToolResult to the format expected by the loop
            for result in streaming_results:
                if result.result:
                    serialized = result.result.to_dict() if hasattr(result.result, "to_dict") else str(result.result)
                else:
                    serialized = json.dumps({"success": False, "error": result.error}) if result.error else "{}"

                working_messages.append(
                    ToolMessage(
                        content=serialized,
                        tool_call_id=result.tool_id,
                    )
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
