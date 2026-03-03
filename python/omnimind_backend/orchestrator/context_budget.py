"""Context budget tracking per agent session.

Monitors token utilization and emits governance events when
thresholds are crossed.
"""

from __future__ import annotations

from omnimind_backend.schemas.context_governance import (
    ContextBudgetConfig,
    ContextEvent,
    ContextEventType,
)


class ContextBudgetTracker:
    """Per-agent, per-session token budget tracker."""

    def __init__(
        self,
        agent_id: str,
        session_id: str,
        config: ContextBudgetConfig | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._session_id = session_id
        self._config = config or ContextBudgetConfig()
        self._current_tokens = 0
        self._warning_emitted = False
        self._enforcement_emitted = False

    @property
    def current_tokens(self) -> int:
        return self._current_tokens

    @property
    def utilization(self) -> float:
        if self._config.hard_limit_tokens == 0:
            return 0.0
        return self._current_tokens / self._config.hard_limit_tokens

    def add_tokens(self, count: int) -> list[ContextEvent]:
        """Add tokens and return any threshold events."""
        self._current_tokens += count
        events: list[ContextEvent] = []
        util = self.utilization

        if util >= self._config.enforcement_threshold and not self._enforcement_emitted:
            events.append(self._make_event(ContextEventType.BUDGET_ENFORCED, util))
            self._enforcement_emitted = True
        elif util >= self._config.warning_threshold and not self._warning_emitted:
            events.append(self._make_event(ContextEventType.BUDGET_WARNING, util))
            self._warning_emitted = True

        return events

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