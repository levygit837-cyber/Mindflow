"""Runtime adapter for UnifiedExecutionEngine integration.

This module provides an adapter layer that integrates the new UnifiedExecutionEngine
into the existing AgentRuntime without breaking backward compatibility.

The adapter:
- Checks feature flags to decide which engine to use
- Converts between old and new execution formats
- Maintains SSE event format compatibility
- Provides graceful fallback to legacy execution
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.execution.types import ExecutionContext
from mindflow_backend.execution.unified_engine import UnifiedExecutionEngine
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.feature_flags import FeatureFlags
from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent
from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy

_logger = get_logger(__name__)


class UnifiedEngineAdapter:
    """Adapter for integrating UnifiedExecutionEngine into AgentRuntime.

    This class bridges the gap between the legacy AgentRuntime interface
    and the new UnifiedExecutionEngine, allowing gradual rollout via
    feature flags.
    """

    def __init__(self):
        self._engine: UnifiedExecutionEngine | None = None

    def is_enabled(self) -> bool:
        """Check if unified engine is enabled via feature flag."""
        return FeatureFlags.unified_engine_enabled()

    def get_engine(self) -> UnifiedExecutionEngine:
        """Get or create the unified engine (lazy init)."""
        if self._engine is None:
            self._engine = UnifiedExecutionEngine(max_global_iterations=1000)
            _logger.info("unified_engine_initialized")

        return self._engine

    async def execute_with_unified_engine(
        self,
        payload: AgentChatRequest,
        session_id: str,
        decision: Any,  # OrchestratorDecision
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute using the unified engine and stream events.

        Args:
            payload: Original request payload
            session_id: Session ID
            decision: Routing decision from IntelligentRouter
            run_id: Optional run ID for tracking

        Yields:
            StreamEvent objects compatible with existing SSE format
        """
        _logger.info(
            "unified_engine_execution_start",
            session_id=session_id,
            strategy=decision.execution_strategy.value,
            agent=decision.agent.value,
        )

        # Build execution context
        context = ExecutionContext(
            decision=decision,
            session_id=session_id,
            message=payload.message,
            provider=payload.provider or "google",
            model=payload.model or "gemini-3.1-flash-lite-preview",
            folder_path=payload.folder_path,
            max_iterations=1000,
            run_id=run_id,
        )

        # Get engine
        engine = self.get_engine()

        # Stream execution
        try:
            async for event_dict in engine.execute_stream(
                strategy=decision.execution_strategy,
                context=context,
            ):
                # Convert dict events to StreamEvent objects
                stream_event = self._convert_to_stream_event(
                    event_dict,
                    session_id=session_id,
                    run_id=run_id or "",
                )
                yield stream_event

        except Exception as exc:
            _logger.error(
                "unified_engine_execution_error",
                error=str(exc),
                session_id=session_id,
            )
            # Yield error event
            yield self._create_error_event(
                error=str(exc),
                session_id=session_id,
                run_id=run_id or "",
            )

    def _convert_to_stream_event(
        self,
        event_dict: dict[str, Any],
        session_id: str,
        run_id: str,
    ) -> StreamEvent:
        """Convert engine event dict to StreamEvent object.

        Args:
            event_dict: Event from unified engine
            session_id: Session ID
            run_id: Run ID

        Returns:
            StreamEvent compatible with existing format
        """
        from mindflow_backend.schemas.chat.agent import StreamEventMeta

        event_type = event_dict.get("type", "response")
        data = event_dict.get("data", "")

        # Create metadata
        meta = StreamEventMeta(
            runId=run_id,
            turnRunId=session_id,
            node="unified_engine",
            nodeCategory="RUNTIME",
            userVisible=True,
        )

        # Add agent info if present
        if "agent" in event_dict:
            meta.agent = event_dict["agent"]

        # Generate event ID
        import uuid
        event_id = f"evt-{uuid.uuid4().hex[:8]}"

        return StreamEvent(
            id=event_id,
            seq=0,  # Will be set by normalizer if needed
            type=event_type,  # type: ignore[arg-type]
            mode="messages",
            data=str(data),
            meta=meta,
        )

    def _create_error_event(
        self,
        error: str,
        session_id: str,
        run_id: str,
    ) -> StreamEvent:
        """Create an error event.

        Args:
            error: Error message
            session_id: Session ID
            run_id: Run ID

        Returns:
            StreamEvent with error
        """
        from mindflow_backend.schemas.chat.agent import StreamEventMeta

        import uuid

        meta = StreamEventMeta(
            runId=run_id,
            turnRunId=session_id,
            node="unified_engine",
            nodeCategory="RUNTIME",
            userVisible=True,
        )

        return StreamEvent(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            seq=0,
            type="error",
            mode="messages",
            data=error,
            meta=meta,
        )

    def should_use_unified_engine(
        self,
        payload: AgentChatRequest,
        execution_mode: str,
    ) -> bool:
        """Determine if unified engine should be used for this request.

        Args:
            payload: Request payload
            execution_mode: Execution mode (orchestrated, direct, legacy)

        Returns:
            True if unified engine should be used
        """
        # Check feature flag
        if not self.is_enabled():
            return False

        # Only use for orchestrated mode initially
        if execution_mode != "orchestrated":
            return False

        # Check if team sessions are involved
        if payload.orchestrate and FeatureFlags.team_sessions_enabled():
            return True

        # Use for delegate strategy
        return True

    def get_execution_strategy(
        self,
        decision: Any,  # OrchestratorDecision
    ) -> ExecutionStrategy:
        """Extract execution strategy from decision.

        Args:
            decision: Routing decision

        Returns:
            ExecutionStrategy enum value
        """
        return decision.execution_strategy
