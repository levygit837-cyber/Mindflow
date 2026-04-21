"""Decomposition strategy — Tasker → Scheduler → Resolver → Synthesizer.

Wraps ``mindflow_backend.decomposition.DecompositionEngine`` as a QueryEngine
strategy. The underlying engine class stays in ``decomposition/engine.py``
until Phase 5 of the unification plan; this strategy is the new
entrypoint used by ``QueryEngine.execute(QueryStrategy.DECOMPOSITION, ...)``.

Contracts ``MainTaskContract`` / ``SubTaskContract`` / ``SynthesisContract``
are preserved verbatim. No field names or method signatures change.
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


class DecompositionStrategy(BaseStrategy):
    """Run the decomposition pipeline as a single strategy."""

    strategy = QueryStrategy.DECOMPOSITION

    async def run(
        self,
        context: StrategyContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        engine = context.services.get("decomposition_engine")
        if engine is None:
            # Lazy-build a default engine using the v2 orchestrator components,
            # mirroring how SimpleOrchestratorGraph wires it today.
            engine = _build_default_engine()

        complexity_score = float(context.metadata.get("complexity_score", 0.5))
        memory_context = str(context.metadata.get("memory_context", ""))

        yield {
            "type": "system",
            "content": "Decomposing task into subtasks…",
            "stage": "decomposition_start",
        }

        try:
            result = await engine.execute(
                message=context.message,
                session_id=context.session_id or "default",
                complexity_score=complexity_score,
                provider=context.provider or "",
                model=context.model or "",
                memory_context=memory_context,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the client
            logger.error(
                "decomposition_strategy_failed",
                session_id=context.session_id,
                error=str(exc),
                exc_info=True,
            )
            yield {
                "type": "system",
                "content": f"Decomposition error: {exc}",
                "is_error": True,
            }
            return

        synthesis = result.get("synthesis")
        response_text = _extract_synthesis_text(synthesis)

        yield {
            "type": "assistant",
            "content": response_text,
            "metadata": {
                "main_contract": _safe_dump(result.get("main_contract")),
                "components_count": len(result.get("components", []) or []),
                "validated_count": len(result.get("validated", []) or []),
            },
        }

        yield {
            "type": "final",
            "content": response_text,
            "synthesis": _safe_dump(synthesis),
        }


def _build_default_engine() -> Any:
    """Build the canonical decomposition engine used by SimpleOrchestratorGraph."""
    from mindflow_backend.decomposition.engine import DecompositionEngine
    from mindflow_backend.orchestrator.decomposition.decomposer_v2 import DecomposerV2
    from mindflow_backend.orchestrator.decomposition.resolver_v2 import ResolverV2
    from mindflow_backend.orchestrator.decomposition.scheduler_v2 import SchedulerV2
    from mindflow_backend.orchestrator.decomposition.synthesizer_v2 import SynthesizerV2

    return DecompositionEngine(
        tasker=DecomposerV2(),
        resolver=ResolverV2(),
        scheduler=SchedulerV2(),
        synthesizer=SynthesizerV2(),
    )


def _extract_synthesis_text(synthesis: Any) -> str:
    """Extract a human-readable response from a SynthesisContract-like object."""
    if synthesis is None:
        return ""
    for attr in ("final_response", "response", "content", "text", "summary"):
        value = getattr(synthesis, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    if isinstance(synthesis, dict):
        for key in ("final_response", "response", "content", "text", "summary"):
            value = synthesis.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return str(synthesis)


def _safe_dump(obj: Any) -> Any:
    """Best-effort JSON-friendly dump of a pydantic model or dict."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:  # noqa: BLE001
            return str(obj)
    return obj
