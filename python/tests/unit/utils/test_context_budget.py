"""Tests for context budget tracking."""

from mindflow_backend.orchestrator.context_budget import ContextBudgetTracker
from mindflow_backend.schemas.context_governance import ContextBudgetConfig, ContextEventType


def test_initial_state() -> None:
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1")
    assert tracker.current_tokens == 0
    assert tracker.utilization == 0.0


def test_add_tokens() -> None:
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1")
    tracker.add_tokens(500_000)
    assert tracker.current_tokens == 500_000


def test_warning_threshold_event() -> None:
    config = ContextBudgetConfig(hard_limit_tokens=100_000)
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1", config=config)
    events = tracker.add_tokens(82_000)  # 82% > 80% warning
    assert any(e.event_type == ContextEventType.BUDGET_WARNING for e in events)


def test_enforcement_threshold_event() -> None:
    config = ContextBudgetConfig(hard_limit_tokens=100_000)
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1", config=config)
    events = tracker.add_tokens(92_000)  # 92% > 90% enforcement
    assert any(e.event_type == ContextEventType.BUDGET_ENFORCED for e in events)


def test_should_force_no_context() -> None:
    config = ContextBudgetConfig(hard_limit_tokens=100_000)
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1", config=config)
    tracker.add_tokens(92_000)
    assert tracker.should_force_no_context() is True


def test_should_trigger_rollup() -> None:
    config = ContextBudgetConfig(hard_limit_tokens=100_000)
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1", config=config)
    tracker.add_tokens(82_000)
    assert tracker.should_trigger_rollup() is True


def test_no_events_below_warning() -> None:
    config = ContextBudgetConfig(hard_limit_tokens=100_000)
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1", config=config)
    events = tracker.add_tokens(50_000)  # 50% < 80% warning
    assert len(events) == 0


def test_reset_after_rollup() -> None:
    config = ContextBudgetConfig(hard_limit_tokens=100_000)
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1", config=config)
    tracker.add_tokens(85_000)  # Trigger warning
    tracker.reset_after_rollup(30_000)  # Free 30k tokens
    assert tracker.current_tokens == 55_000
    assert tracker.utilization == 0.55


def test_event_details() -> None:
    config = ContextBudgetConfig(hard_limit_tokens=100_000)
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1", config=config)
    events = tracker.add_tokens(82_000)
    
    assert len(events) == 1
    event = events[0]
    assert event.agent_id == "coder"
    assert event.session_id == "s1"
    assert event.current_tokens == 82_000
    assert event.budget_limit == 100_000
    assert event.utilization_pct == 0.82


def test_no_duplicate_events() -> None:
    """Ensure warning/enforcement events are only emitted once."""
    config = ContextBudgetConfig(hard_limit_tokens=100_000)
    tracker = ContextBudgetTracker(agent_id="coder", session_id="s1", config=config)
    
    # First time crossing warning threshold
    events1 = tracker.add_tokens(82_000)
    assert len(events1) == 1
    assert events1[0].event_type == ContextEventType.BUDGET_WARNING
    
    # Adding more tokens should not emit another warning
    events2 = tracker.add_tokens(5_000)
    assert len(events2) == 0
    
    # But crossing enforcement threshold should emit enforcement event
    events3 = tracker.add_tokens(5_000)  # Now at 92%
    assert len(events3) == 1
    assert events3[0].event_type == ContextEventType.BUDGET_ENFORCED