"""Unified Execution Engine - Central coordinator for all agent executions.

This module provides the UnifiedExecutionEngine class, which serves as the
single entry point for all execution strategies in MindFlow.

It replaces the fragmented execution logic scattered across:
- invoke_with_tools() / stream_with_tools()
- Deep Work Loop
- Planning Execution Loop
- Various node executors

With a single, unified, observable, and controllable execution system.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy

from .loops.tool_loop import ToolExecutionLoop
from .types import ExecutionContext, ExecutionResult, ExecutionState, ExecutionStatus

_logger = get_logger(__name__)


class ExecutionCoordinator:
    """Coordinates execution state and iteration control.

    This is the internal brain of the UnifiedExecutionEngine that:
    - Tracks global iteration count across all loops
    - Enforces iteration limits
    - Manages timeouts
    - Coordinates between different loop types
    """

    def __init__(self, max_global_iterations: int = 1000):
        self.max_global_iterations = max_global_iterations
        self.current_global_iteration = 0

    def can_continue(self, state: ExecutionState) -> bool:
        """Check if execution can continue."""
        if state.status != ExecutionStatus.RUNNING:
            return False

        if self.current_global_iteration >= self.max_global_iterations:
            _logger.warning(
                "global_iteration_limit_reached",
                current=self.current_global_iteration,
                max=self.max_global_iterations,
            )
            return False

        return True

    def increment_iteration(self, state: ExecutionState) -> None:
        """Increment iteration counters."""
        self.current_global_iteration += 1
        state.current_iteration += 1

    def reset(self) -> None:
        """Reset coordinator state for new execution."""
        self.current_global_iteration = 0


class UnifiedExecutionEngine:
    """Unified execution engine for all agent strategies.

    This is the single entry point for executing any agent task, regardless
    of strategy (DELEGATE, TEAM_SESSION, CHAIN, GRAPH, etc.).

    Architecture:
        UnifiedExecutionEngine
            ├─ ExecutionCoordinator (iteration control)
            ├─ ToolExecutionLoop (ReAct pattern)
            ├─ TeamExecutionLoop (collaborative sessions)
            └─ WorkExecutionLoop (deep work)

    Usage:
        engine = UnifiedExecutionEngine()
        result = await engine.execute(strategy, context)
    """

    def __init__(self, max_global_iterations: int = 1000):
        """Initialize the unified engine.

        Args:
            max_global_iterations: Maximum iterations across all loops
        """
        self.settings = get_settings()
        self.coordinator = ExecutionCoordinator(max_global_iterations)

        # Lazy-loaded components
        self._team_manager: Any = None

    async def execute(
        self,
        strategy: ExecutionStrategy,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Execute a task with the specified strategy.

        This is the main entry point for all executions.

        Args:
            strategy: Execution strategy to use
            context: Execution context with all parameters

        Returns:
            ExecutionResult with response and metadata
        """
        _logger.info(
            "unified_engine_execute_start",
            strategy=strategy.value,
            session_id=context.session_id,
            agent=context.decision.agent.value,
        )

        # Create execution state
        state = ExecutionState()
        state.mark_started()

        # Reset coordinator for new execution
        self.coordinator.reset()

        try:
            # Dispatch to appropriate executor
            if strategy == ExecutionStrategy.DELEGATE:
                result = await self._execute_single_agent(context, state)
            elif strategy == ExecutionStrategy.TEAM_SESSION:
                result = await self._execute_team_session(context, state)
            elif strategy == ExecutionStrategy.CHAIN:
                result = await self._execute_chain(context, state)
            elif strategy == ExecutionStrategy.GRAPH:
                result = await self._execute_graph(context, state)
            elif strategy == ExecutionStrategy.DIRECT_RESPONSE:
                result = await self._execute_direct_response(context, state)
            else:
                raise ValueError(f"Unknown execution strategy: {strategy}")

            state.mark_completed()
            return result

        except Exception as exc:
            _logger.error(
                "unified_engine_execute_error",
                error=str(exc),
                strategy=strategy.value,
            )
            state.mark_failed(str(exc))
            return ExecutionResult.from_state(
                state=state,
                response="",
                success=False,
                error=str(exc),
            )

    async def execute_stream(
        self,
        strategy: ExecutionStrategy,
        context: ExecutionContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute with streaming events.

        Yields stream events compatible with the existing SSE format.

        Args:
            strategy: Execution strategy
            context: Execution context

        Yields:
            Stream events (dict format)
        """
        _logger.info(
            "unified_engine_execute_stream_start",
            strategy=strategy.value,
            session_id=context.session_id,
        )

        state = ExecutionState()
        state.mark_started()
        self.coordinator.reset()

        try:
            if strategy == ExecutionStrategy.DELEGATE:
                async for event in self._stream_single_agent(context, state):
                    yield event
            elif strategy == ExecutionStrategy.TEAM_SESSION:
                async for event in self._stream_team_session(context, state):
                    yield event
            else:
                # Fallback: execute non-streaming and yield result
                result = await self.execute(strategy, context)
                yield {
                    "type": "response",
                    "data": result.response,
                }
                yield {"type": "done"}

        except Exception as exc:
            _logger.error("unified_engine_stream_error", error=str(exc))
            yield {
                "type": "error",
                "data": str(exc),
            }

    # ─────────────────────────────────────────────────────────────────
    # Single Agent Execution (DELEGATE strategy)
    # ─────────────────────────────────────────────────────────────────

    async def _execute_single_agent(
        self,
        context: ExecutionContext,
        state: ExecutionState,
    ) -> ExecutionResult:
        """Execute single agent with tools (non-streaming)."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
        from mindflow_backend.infra.llm import get_model_for_provider

        # Get agent and tools
        agent_id = context.decision.agent_id or context.decision.agent.value
        tools = self._get_tools_for_agent(context)
        lc_tools = to_langchain_tools(tools) if tools else []

        # Build messages
        messages = self._build_messages(context)

        # Get LLM
        llm = get_model_for_provider(context.provider, context.model)

        # Execute with tool loop
        if lc_tools:
            llm_with_tools = llm.bind_tools(lc_tools)
            tool_loop = ToolExecutionLoop(
                max_iterations=context.max_iterations,
                event_dispatcher=self._make_event_dispatcher(state),
                before_iteration=self._make_before_iteration(state),
                session_id=context.session_id,
            )

            loop_result = await tool_loop.run(
                llm=llm_with_tools,
                messages=messages,
                lc_tools=lc_tools,
                stream=False,
            )

            return ExecutionResult.from_state(
                state=state,
                response=loop_result.final_response,
                success=True,
            )
        else:
            # No tools - direct LLM call
            response = await llm.ainvoke(messages)
            from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts

            _, texts = extract_chunk_parts(response)
            final_text = "".join(texts)

            return ExecutionResult.from_state(
                state=state,
                response=final_text,
                success=True,
            )

    async def _stream_single_agent(
        self,
        context: ExecutionContext,
        state: ExecutionState,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute single agent with streaming."""
        from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
        from mindflow_backend.infra.llm import get_model_for_provider

        tools = self._get_tools_for_agent(context)
        lc_tools = to_langchain_tools(tools) if tools else []
        messages = self._build_messages(context)
        llm = get_model_for_provider(context.provider, context.model)

        # Event queue for streaming
        import asyncio
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

        async def chunk_dispatcher(text: str) -> None:
            await queue.put(("chunk", text))

        async def event_dispatcher(name: str, payload: dict) -> None:
            await queue.put(("event", (name, payload)))

        # Run tool loop in background
        async def runner() -> None:
            try:
                if lc_tools:
                    llm_with_tools = llm.bind_tools(lc_tools)
                    tool_loop = ToolExecutionLoop(
                        max_iterations=context.max_iterations,
                        event_dispatcher=event_dispatcher,
                        chunk_dispatcher=chunk_dispatcher,
                        session_id=context.session_id,
                    )
                    await tool_loop.run(
                        llm=llm_with_tools,
                        messages=messages,
                        lc_tools=lc_tools,
                        stream=True,
                    )
                else:
                    async for chunk in llm.astream(messages):
                        from mindflow_backend.runtime.streaming.chunk_extract import (
                            extract_chunk_parts,
                        )

                        _, texts = extract_chunk_parts(chunk)
                        for text in texts:
                            await chunk_dispatcher(text)
            except Exception as exc:
                await queue.put(("error", exc))
            finally:
                await queue.put(("done", None))

        import asyncio
        task = asyncio.create_task(runner())

        try:
            while True:
                event_kind, payload = await queue.get()

                if event_kind == "done":
                    yield {"type": "done"}
                    break
                elif event_kind == "error":
                    yield {"type": "error", "data": str(payload)}
                    break
                elif event_kind == "chunk":
                    yield {"type": "response", "data": payload}
                elif event_kind == "event":
                    name, data = payload
                    yield {"type": "agent_event", "name": name, "data": data}
        finally:
            if not task.done():
                task.cancel()

    # ─────────────────────────────────────────────────────────────────
    # Team Session Execution (TEAM_SESSION strategy)
    # ─────────────────────────────────────────────────────────────────

    async def _execute_team_session(
        self,
        context: ExecutionContext,
        state: ExecutionState,
    ) -> ExecutionResult:
        """Execute team session (collaborative multi-agent)."""
        team_manager = self._get_team_manager()

        # Extract team configuration from metadata
        metadata = context.decision.metadata or {}
        agent_ids = metadata.get("team_agent_ids", [])

        if not agent_ids:
            return ExecutionResult.from_state(
                state=state,
                response="No agents specified for team session",
                success=False,
                error="Missing team_agent_ids in metadata",
            )

        # Run team session
        from mindflow_backend.execution.teams.team_orchestrator import TeamOrchestrator

        team_orchestrator = TeamOrchestrator(
            team_manager=team_manager,
            mission_launcher=None,  # TODO: inject when available
            comm_bus=None,  # TODO: inject when available
        )

        team_result = await team_orchestrator.run_full_team_session(
            task=context.message,
            agent_ids=agent_ids,
            session_id=context.session_id,
        )

        state.mission_results = team_result.mission_results
        state.mission_dag = team_result.mission_dag

        return ExecutionResult.from_state(
            state=state,
            response=team_result.synthesized_response,
            success=team_result.success,
        )

    async def _stream_team_session(
        self,
        context: ExecutionContext,
        state: ExecutionState,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream team session execution."""
        # TODO: Implement streaming for team sessions
        # For now, execute non-streaming and yield result
        result = await self._execute_team_session(context, state)
        yield {"type": "response", "data": result.response}
        yield {"type": "done"}

    # ─────────────────────────────────────────────────────────────────
    # Other Strategies (CHAIN, GRAPH, DIRECT_RESPONSE)
    # ─────────────────────────────────────────────────────────────────

    async def _execute_chain(
        self,
        context: ExecutionContext,
        state: ExecutionState,
    ) -> ExecutionResult:
        """Execute chain strategy."""
        # TODO: Implement chain execution
        return ExecutionResult.from_state(
            state=state,
            response="Chain execution not yet implemented",
            success=False,
            error="Not implemented",
        )

    async def _execute_graph(
        self,
        context: ExecutionContext,
        state: ExecutionState,
    ) -> ExecutionResult:
        """Execute graph strategy."""
        # TODO: Implement graph execution
        return ExecutionResult.from_state(
            state=state,
            response="Graph execution not yet implemented",
            success=False,
            error="Not implemented",
        )

    async def _execute_direct_response(
        self,
        context: ExecutionContext,
        state: ExecutionState,
    ) -> ExecutionResult:
        """Execute direct response (orchestrator responds without delegation)."""
        from mindflow_backend.infra.llm import get_model_for_provider

        messages = self._build_messages(context)
        llm = get_model_for_provider(context.provider, context.model)

        response = await llm.ainvoke(messages)
        from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts

        _, texts = extract_chunk_parts(response)
        final_text = "".join(texts)

        return ExecutionResult.from_state(
            state=state,
            response=final_text,
            success=True,
        )

    # ─────────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────────

    def _get_tools_for_agent(self, context: ExecutionContext) -> list[Any]:
        """Get tools for the agent based on decision."""
        from mindflow_backend.agents.tools import get_tools_for_scopes

        tool_scopes = context.decision.tools or []
        if not tool_scopes:
            return []

        return get_tools_for_scopes(
            tool_scopes,
            sandbox_root=context.folder_path,
        )

    def _build_messages(self, context: ExecutionContext) -> list[dict[str, Any]]:
        """Build message list for LLM."""
        from mindflow_backend.agents.prompts import get_system_prompt_for_agent

        messages = []

        # System prompt
        system_prompt = get_system_prompt_for_agent(
            agent_type=context.decision.agent,
            specialist=context.decision.specialist,
        )
        messages.append({"role": "system", "content": system_prompt})

        # Conversation history
        messages.extend(context.conversation_history)

        # Current message
        messages.append({"role": "user", "content": context.message})

        return messages

    def _make_event_dispatcher(
        self,
        state: ExecutionState,
    ) -> Any:
        """Create event dispatcher for tool loop."""

        async def dispatcher(name: str, payload: dict) -> None:
            state.add_event(name, payload)
            if name == "tool_call_start":
                state.add_tool_call(payload.get("tool", ""), payload.get("args", {}))

        return dispatcher

    def _make_before_iteration(
        self,
        state: ExecutionState,
    ) -> Any:
        """Create before_iteration callback."""

        async def callback(messages: list[Any], iteration: int) -> None:
            self.coordinator.increment_iteration(state)
            if not self.coordinator.can_continue(state):
                raise RuntimeError("Iteration limit reached")

        return callback

    def _get_team_manager(self) -> Any:
        """Get or create team manager (lazy init)."""
        if self._team_manager is None:
            from mindflow_backend.communication.teams.team_manager import TeamManager

            self._team_manager = TeamManager()

        return self._team_manager
