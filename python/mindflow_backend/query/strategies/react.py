"""ReAct strategy — Claude Code ``query.ts``-style while-true loop.

This is the canonical location for the ReAct loop that used to live in
``mindflow_backend.query.query_loop`` (which is kept as a thin backward-compat
shim). Behavior is preserved byte-for-byte; only the class wrapper is new.

Loop shape:
1. Execute orchestrator with current messages.
2. Yield assistant message.
3. Collect tool_use blocks from the response.
4. If none, terminate.
5. Execute tools sequentially; yield tool_result events.
6. Increment turn counter, repeat.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.strategies.base import (
    BaseStrategy,
    QueryStrategy,
    StrategyContext,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only
    from mindflow_backend.agents.base.agent_interface import AgentInterface
    from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
    from mindflow_backend.schemas.orchestration.orchestrator import OrchestratorSession

logger = get_logger(__name__)


@dataclass
class ReActLoopState:
    """Mutable state carried between loop iterations."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    max_turns: int = 50
    tool_use_context: dict[str, Any] = field(default_factory=dict)
    token_budget: TokenBudget | None = None
    session: OrchestratorSession | None = None
    session_id: str | None = None
    execution_id: str | None = None


class ReActStrategy(BaseStrategy):
    """Execute the ReAct loop using the orchestrator + available tools."""

    strategy = QueryStrategy.REACT

    async def run(
        self,
        context: StrategyContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        orchestrator = context.services.get("orchestrator")
        if orchestrator is None:
            raise ValueError("ReActStrategy requires 'orchestrator' in context.services")

        async for event in react_loop(
            initial_message=context.message,
            orchestrator=orchestrator,
            tools=context.tools,
            max_turns=context.max_turns,
            token_budget=context.token_budget,
            session=context.session,
            session_id=context.session_id,
            execution_id=context.execution_id,
        ):
            yield event


async def react_loop(
    initial_message: str,
    orchestrator: AgentInterface,
    tools: list[AsyncToolInterface],
    max_turns: int = 50,
    token_budget: TokenBudget | None = None,
    session: OrchestratorSession | None = None,
    session_id: str | None = None,
    execution_id: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Main execution loop that continues while the orchestrator uses tools.

    Follows Claude Code ``query.ts``:

    1. Execute Orchestrator with current messages
    2. Yield assistant message
    3. Collect tool_use blocks
    4. If no tool_use, terminate
    5. Execute tools (AgentTool delegates to sub-agents)
    6. Yield tool results
    7. Increment turn count and continue
    """
    state = ReActLoopState(
        messages=[{"role": "user", "content": initial_message}],
        turn_count=0,
        max_turns=max_turns,
        token_budget=token_budget or TokenBudget(max_tokens=200_000),
        session=session,
        session_id=session_id,
        execution_id=execution_id,
    )

    logger.info(
        "react_loop_started",
        max_turns=max_turns,
        token_budget=state.token_budget.max_tokens if state.token_budget else None,
    )

    while True:
        # 1. Check limits
        if state.turn_count >= state.max_turns:
            logger.info("react_loop_max_turns_reached", turns=state.turn_count)
            yield {
                "type": "system",
                "content": f"Max turns ({state.max_turns}) reached. Stopping execution.",
            }
            break

        if state.token_budget and state.token_budget.remaining_tokens <= 0:
            logger.info("react_loop_token_budget_exhausted")
            yield {
                "type": "system",
                "content": "Token budget exhausted. Stopping execution.",
            }
            break

        # 2. Execute Orchestrator with current messages
        logger.debug(
            "react_loop_turn_start",
            turn=state.turn_count,
            message_count=len(state.messages),
        )

        try:
            context_payload = {
                **state.tool_use_context,
                "session": state.session,
                "session_id": state.session_id,
                "execution_id": state.execution_id,
            }

            response = await orchestrator.ainvoke(
                state.messages,
                tools=tools,
                context=context_payload,
            )

            # 3. Yield assistant message
            assistant_message: dict[str, Any] = {
                "type": "assistant",
                "content": response.content if hasattr(response, "content") else str(response),
            }
            yield assistant_message
            state.messages.append(assistant_message)

            # 4. Collect tool_use blocks
            tool_use_blocks = _extract_tool_use_blocks(response)

            # 5. If no tool_use, terminate
            if not tool_use_blocks:
                logger.info("react_loop_no_tool_use", turn=state.turn_count)
                break

            # 6. Execute tools
            for tool_use in tool_use_blocks:
                tool_name = tool_use.get("name")
                tool_input = tool_use.get("input", {})
                tool_id = tool_use.get("id")

                logger.debug("react_loop_tool_use", tool_name=tool_name, tool_id=tool_id)

                tool = _find_tool(tools, tool_name)
                if tool is None:
                    error_msg = f"Tool '{tool_name}' not found"
                    logger.warning("react_loop_tool_not_found", tool_name=tool_name)
                    yield {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": error_msg,
                        "is_error": True,
                    }
                    state.messages.append(
                        {
                            "role": "tool_result",
                            "tool_use_id": tool_id,
                            "content": error_msg,
                        }
                    )
                    continue

                try:
                    result = await tool.execute(**tool_input)
                    tool_result_message: dict[str, Any] = {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result,
                    }
                    yield tool_result_message
                    state.messages.append(tool_result_message)

                except Exception as exc:  # noqa: BLE001 - surfaced to the client
                    error_msg = f"Tool execution error: {exc}"
                    logger.error(
                        "react_loop_tool_error",
                        tool_name=tool_name,
                        error=str(exc),
                    )
                    yield {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": error_msg,
                        "is_error": True,
                    }
                    state.messages.append(
                        {
                            "role": "tool_result",
                            "tool_use_id": tool_id,
                            "content": error_msg,
                        }
                    )

            # 7. Increment turn count
            state.turn_count += 1
            logger.debug("react_loop_turn_complete", turn=state.turn_count)

        except Exception as exc:  # noqa: BLE001 - surfaced to the client
            logger.error("react_loop_error", error=str(exc), exc_info=True)
            yield {
                "type": "system",
                "content": f"ReAct loop error: {exc}",
            }
            break

    logger.info(
        "react_loop_completed",
        total_turns=state.turn_count,
        final_message_count=len(state.messages),
    )


def _extract_tool_use_blocks(response: Any) -> list[dict[str, Any]]:
    """Extract tool_use blocks from agent response."""
    tool_use_blocks: list[dict[str, Any]] = []

    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            if isinstance(tool_call, dict):
                tool_use_blocks.append(
                    {
                        "name": tool_call.get("name"),
                        "input": tool_call.get("input", {}),
                        "id": tool_call.get("id"),
                    }
                )
            else:
                tool_use_blocks.append(
                    {
                        "name": tool_call.function.name
                        if hasattr(tool_call.function, "name")
                        else getattr(tool_call, "name", None),
                        "input": tool_call.function.arguments
                        if hasattr(tool_call.function, "arguments")
                        else getattr(tool_call, "input", {}),
                        "id": tool_call.id if hasattr(tool_call, "id") else getattr(tool_call, "id", None),
                    }
                )

    elif hasattr(response, "structured_tool_calls") and response.structured_tool_calls:
        for tool_call in response.structured_tool_calls:
            if isinstance(tool_call, dict):
                tool_use_blocks.append(
                    {
                        "name": tool_call.get("name"),
                        "input": tool_call.get("input", {}),
                        "id": tool_call.get("id"),
                    }
                )
            else:
                tool_use_blocks.append(
                    {
                        "name": tool_call.name
                        if hasattr(tool_call, "name")
                        else getattr(tool_call, "name", None),
                        "input": tool_call.args
                        if hasattr(tool_call, "args")
                        else getattr(tool_call, "input", {}),
                        "id": tool_call.id if hasattr(tool_call, "id") else getattr(tool_call, "id", None),
                    }
                )

    return tool_use_blocks


def _find_tool(
    tools: list[AsyncToolInterface], tool_name: str | None
) -> AsyncToolInterface | None:
    """Find a tool by name."""
    if not tool_name:
        return None
    for tool in tools:
        if hasattr(tool, "name") and tool.name == tool_name:
            return tool
    return None
