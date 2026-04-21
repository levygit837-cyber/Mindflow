"""Strategy selector and StrategyContext builder for the unified kernel.

``select_strategy()``   — maps an ``AgentChatRequest`` to a ``QueryStrategy``.
``build_strategy_context()`` — constructs a ``StrategyContext`` from the request
                               and the runtime services available.

Both functions are pure (no side-effects) and designed to be unit-tested
without the full runtime stack.

Phase 3 of the unified-engine plan — see
.windsurf/plans/unified-engine-47796c.md §4.3.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.query.strategies.base import QueryStrategy, StrategyContext

if TYPE_CHECKING:  # pragma: no cover
    from mindflow_backend.schemas.chat.agent import AgentChatRequest


def select_strategy(payload: AgentChatRequest) -> QueryStrategy:
    """Map a chat request to the appropriate ``QueryStrategy``.

    Priority order (mirrors legacy routing in ``AgentRuntime.stream_chat``):

    1. Orchestrate + structured flow  → DECOMPOSITION
    2. Explicit ``agent_type``        → DIRECT
    3. Legacy (no flags)              → REACT

    Strategy override via ``QUERYENGINE_STRATEGY_OVERRIDE`` env var is
    honoured when set (useful for testing/debugging).
    """
    settings = get_settings()
    override = getattr(settings, "queryengine_strategy_override", None)
    if override:
        return QueryStrategy(override)

    if _is_orchestrated(payload):
        return QueryStrategy.DECOMPOSITION

    if getattr(payload, "agent_type", None):
        return QueryStrategy.DIRECT

    return QueryStrategy.REACT


def build_strategy_context(
    payload: AgentChatRequest,
    *,
    session_id: str,
    execution_id: str | None = None,
    run_id: str | None = None,
    tools: list[Any] | None = None,
    services: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> StrategyContext:
    """Build a ``StrategyContext`` from an ``AgentChatRequest`` and runtime deps.

    Services passed here are injected by the routing layer; the strategies
    themselves never import from ``AgentRuntime`` or any service registry.
    """
    settings = get_settings()
    provider = getattr(payload, "provider", None) or settings.default_provider
    model = getattr(payload, "model", None) or settings.default_model

    ctx_metadata: dict[str, Any] = {
        "orchestrate": bool(getattr(payload, "orchestrate", False)),
        "folder_path": getattr(payload, "folder_path", None),
        "run_id": run_id,
    }
    if metadata:
        ctx_metadata.update(metadata)

    return StrategyContext(
        message=payload.message,
        session_id=session_id,
        execution_id=execution_id,
        provider=provider,
        model=model,
        agent_type=getattr(payload, "agent_type", None),
        tools=tools or [],
        max_turns=getattr(settings, "max_agent_iterations", 50),
        max_depth=getattr(settings, "max_deep_work_depth", 1000),
        services=services or {},
        metadata=ctx_metadata,
    )


def _is_orchestrated(payload: AgentChatRequest) -> bool:
    """True when this payload should go through the orchestrated/decomposition path."""
    if getattr(payload, "orchestrate", False):
        return True
    agent_type = (getattr(payload, "agent_type", None) or "").strip().lower()
    if agent_type == "analyst":
        folder = getattr(payload, "folder_path", None)
        message = getattr(payload, "message", "")
        keywords = ["analys", "review", "audit", "report"]
        if folder or any(k in message.lower() for k in keywords):
            return True
    return False
