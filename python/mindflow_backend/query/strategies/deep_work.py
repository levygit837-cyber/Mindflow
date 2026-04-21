"""Deep Work strategy — multi-turn continuation protocol.

Ports the Deep Work Loop that previously lived inline in
``nodes/implementations/orchestrator/execute_node.py``. An agent keeps
investigating as long as ``should_continue_investigation()`` (from
``orchestrator/deep_work.py``) returns True, capped by ``max_depth``.

Keeps the exact semantics of the legacy loop:

- accumulated response joined with ``--- CONTINUATION TURN N ---`` markers
- short summaries (first 200 chars per turn) stored as investigation_history
- continuation context built via ``build_continuation_context()``
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.deep_work import (
    build_continuation_context,
    should_continue_investigation,
)
from mindflow_backend.query.strategies.base import (
    BaseStrategy,
    QueryStrategy,
    StrategyContext,
)

logger = get_logger(__name__)

_DEFAULT_MAX_DEPTH = 1000


class DeepWorkStrategy(BaseStrategy):
    """Multi-turn continuation loop over a single agent."""

    strategy = QueryStrategy.DEEP_WORK

    async def run(
        self,
        context: StrategyContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        agent = context.services.get("agent")
        if agent is None:
            raise ValueError(
                "DeepWorkStrategy requires 'agent' in context.services"
            )

        max_depth = context.max_depth or _DEFAULT_MAX_DEPTH
        investigation_history: list[str] = []
        accumulated_response = ""
        current_message = context.message
        current_depth = 0

        logger.info(
            "deep_work_strategy_started",
            session_id=context.session_id,
            agent_type=context.agent_type,
            max_depth=max_depth,
        )

        while current_depth < max_depth:
            try:
                response_obj = await agent.ainvoke(
                    [{"role": "user", "content": current_message}],
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
                    "deep_work_strategy_invoke_failed",
                    session_id=context.session_id,
                    depth=current_depth,
                    error=str(exc),
                    exc_info=True,
                )
                yield {
                    "type": "system",
                    "content": f"Deep Work error at depth {current_depth}: {exc}",
                    "is_error": True,
                }
                break

            response_text = (
                response_obj.content
                if hasattr(response_obj, "content")
                else str(response_obj)
            )

            # Accumulate response with continuation marker (legacy format preserved)
            if accumulated_response:
                accumulated_response += (
                    f"\n\n--- CONTINUATION TURN {current_depth + 1} ---\n\n{response_text}"
                )
            else:
                accumulated_response = response_text

            yield {
                "type": "assistant",
                "content": response_text,
                "depth": current_depth,
            }

            # Decide whether to continue
            should_continue, reason = should_continue_investigation(
                response_text, current_depth, max_depth
            )

            if not should_continue:
                logger.info(
                    "deep_work_strategy_completed",
                    session_id=context.session_id,
                    depth=current_depth,
                    reason=reason,
                )
                break

            logger.info(
                "deep_work_strategy_continuing",
                session_id=context.session_id,
                depth=current_depth,
                reason=reason,
            )
            investigation_history.append(response_text[:200])
            current_depth += 1
            current_message = build_continuation_context(
                previous_response=response_text,
                investigation_history=investigation_history,
                current_depth=current_depth,
            )

        yield {
            "type": "final",
            "content": accumulated_response,
            "depth": current_depth,
            "turns": current_depth + 1,
        }
