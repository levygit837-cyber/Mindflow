"""Context budget tracking per agent session.

Monitors token utilization and emits governance events when
thresholds are crossed. Enhanced with window tracking capabilities.
"""

from __future__ import annotations

from mindflow_backend.infra.config import get_settings
from mindflow_backend.orchestrator.context_control_arch import (
    context_control_arch,
    is_window_boundary_crossed,
)
from mindflow_backend.schemas.session.governance import (
    ContextBudgetConfig,
    ContextEvent,
    ContextEventType,
)
from mindflow_backend.schemas.session.contracts import ContextControlResult, SessionReview


class ContextBudgetTracker:
    """Per-agent, per-session token budget tracker with window tracking."""

    def __init__(
        self,
        agent_id: str,
        session_id: str,
        config: ContextBudgetConfig | None = None,
        execution_window_size: int | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._session_id = session_id
        self._config = config or ContextBudgetConfig()
        
        # Window tracking
        settings = get_settings()
        self._execution_window_size = execution_window_size or settings.execution_window_size
        self._current_window_position = 0
        self._session_review: SessionReview | None = None
        
        # Traditional budget tracking
        self._current_tokens = 0
        self._warning_emitted = False
        self._enforcement_emitted = False

    @property
    def current_window_position(self) -> int:
        """Current execution window position."""
        return self._current_window_position

    @property
    def session_review(self) -> SessionReview | None:
        """Current session review."""
        return self._session_review

    @property
    def execution_window_size(self) -> int:
        """Size of execution windows."""
        return self._execution_window_size

    @property
    def current_tokens(self) -> int:
        return self._current_tokens

    @property
    def utilization(self) -> float:
        if self._config.hard_limit_tokens == 0:
            return 0.0
        return self._current_tokens / self._config.hard_limit_tokens

    async def add_tokens(self, count: int) -> list[ContextEvent]:
        """Add tokens and return any threshold events."""
        previous_tokens = self._current_tokens
        self._current_tokens += count
        events: list[ContextEvent] = []
        util = self.utilization

        # Check for window boundary crossing
        if is_window_boundary_crossed(previous_tokens, self._current_tokens, self._execution_window_size):
            await self._handle_window_boundary_crossed()

        # Traditional budget events
        if util >= self._config.enforcement_threshold and not self._enforcement_emitted:
            events.append(self._make_event(ContextEventType.BUDGET_ENFORCED, util))
            self._enforcement_emitted = True
        elif util >= self._config.warning_threshold and not self._warning_emitted:
            events.append(self._make_event(ContextEventType.BUDGET_WARNING, util))
            self._warning_emitted = True

        return events

    async def _handle_window_boundary_crossed(self) -> None:
        """Handle crossing of execution window boundary."""
        try:
            # Call context_control_arch to handle window transition
            result = await context_control_arch(
                session_id=self._session_id,
                current_tokens=self._current_tokens,
                execution_window_size=self._execution_window_size,
                existing_session=self._session_review,
            )
            
            # Update session state
            if result.session_review:
                self._session_review = result.session_review
                self._current_window_position = result.window_info.current_window_index
            
            # Log the window transition
            from mindflow_backend.infra.logging import get_logger
            _logger = get_logger(__name__)
            _logger.info(
                "window_boundary_crossed",
                agent_id=self._agent_id,
                session_id=self._session_id,
                previous_window=self._current_window_position,
                new_window=result.window_info.current_window_index,
                action=result.action_taken,
            )
            
        except Exception as exc:
            from mindflow_backend.infra.logging import get_logger
            _logger = get_logger(__name__)
            _logger.error(
                "window_boundary_handling_failed",
                agent_id=self._agent_id,
                session_id=self._session_id,
                error=str(exc),
            )

    def get_current_window_bounds(self) -> tuple[int, int]:
        """Get the bounds of the current execution window."""
        start = self._current_window_position * self._execution_window_size
        end = (self._current_window_position + 1) * self._execution_window_size
        return start, end

    def get_window_info(self) -> dict[str, int | tuple[int, int]]:
        """Get comprehensive window information."""
        start, end = self.get_current_window_bounds()
        return {
            "current_window": self._current_window_position,
            "window_bounds": (start, end),
            "window_size": self._execution_window_size,
            "tokens_in_window": self._current_tokens - start,
            "tokens_until_next_window": end - self._current_tokens,
        }

    def should_force_no_context(self) -> bool:
        """True if enforcement threshold is exceeded."""
        return self.utilization >= self._config.enforcement_threshold

    def should_trigger_rollup(self) -> bool:
        """True if warning threshold is exceeded (rollup oldest context)."""
        return self.utilization >= self._config.warning_threshold

    def reset_after_rollup(self, tokens_freed: int) -> None:
        """Reduce token count after rollup summarization."""
        self._current_tokens = max(0, self._current_tokens - tokens_freed)
        self._warning_emitted = False
        self._enforcement_emitted = False

    def _make_event(self, event_type: ContextEventType, util: float) -> ContextEvent:
        return ContextEvent(
            event_type=event_type,
            agent_id=self._agent_id,
            session_id=self._session_id,
            current_tokens=self._current_tokens,
            budget_limit=self._config.hard_limit_tokens,
            utilization_pct=round(util, 4),
        )