"""Direct strategy — single agent invocation, no tool loop.

Mirrors the ``agent_type`` path that used to live inline in
``AgentRuntime._stream_chat_direct_agent``. The strategy does a single LLM call
through the requested agent and yields the response as one ``assistant`` event.
Useful when orchestration/routing is not needed (e.g. the frontend already
chose a specialist agent).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.query.strategies.base import (
    BaseStrategy,
    QueryStrategy,
    StrategyContext,
)

logger = get_logger(__name__)


class DirectStrategy(BaseStrategy):
    """Invoke a single agent and yield its response. No tool loop."""

    strategy = QueryStrategy.DIRECT

    async def run(
        self,
        context: StrategyContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        agent = context.services.get("agent")
        if agent is None:
            raise ValueError(
                "DirectStrategy requires 'agent' in context.services"
            )

        messages = context.messages or [
            {"role": "user", "content": context.message}
        ]

        logger.debug(
            "direct_strategy_invoke",
            session_id=context.session_id,
            agent_type=context.agent_type,
            provider=context.provider,
            model=context.model,
            message_count=len(messages),
        )

        try:
            response = await agent.ainvoke(
                messages,
                tools=context.tools,
                context={
                    "session": context.session,
                    "session_id": context.session_id,
                    "execution_id": context.execution_id,
                    "provider": context.provider,
                    "model": context.model,
                    "agent_type": context.agent_type,
                },
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the client
            logger.error(
                "direct_strategy_failed",
                session_id=context.session_id,
                error=str(exc),
                exc_info=True,
            )
            yield {
                "type": "system",
                "content": f"Direct strategy error: {exc}",
                "is_error": True,
            }
            return

        content = response.content if hasattr(response, "content") else str(response)
        yield {"type": "assistant", "content": content}
        yield {"type": "done"}
