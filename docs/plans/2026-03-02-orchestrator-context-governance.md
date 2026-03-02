# Orchestrator Context Governance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add context budget enforcement, explorer-to-orchestrator summarization contracts, no-raw-context guard, rollup triggers, and context quality gates to the existing orchestrator and memory system.

**Architecture:** Extends the existing `AgentMemoryService` with per-agent token budgets and summarization triggers. Adds a `ContextGovernor` class that wraps quality gates, budget checks, and rollup logic. Emits structured events for observability. All features are opt-in via config flags.

**Tech Stack:** Python 3.12, Pydantic v2, SQLAlchemy, pytest, existing `memory/service.py` and `orchestrator/graph.py`

---

## Task 1: Context Budget Config and Schema

**Files:**
- Create: `python/omnimind_backend/schemas/context_governance.py`
- Test: `python/tests/test_context_governance_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_context_governance_schemas.py`:

```python
"""Tests for context governance schemas."""

from omnimind_backend.schemas.context_governance import (
    ContextBudgetConfig,
    ContextScope,
    ExplorerSummary,
    ContextEvent,
    ContextEventType,
)


def test_budget_config_defaults() -> None:
    cfg = ContextBudgetConfig()
    assert cfg.warning_threshold == 0.80
    assert cfg.enforcement_threshold == 0.90
    assert cfg.hard_limit_tokens == 1_000_000
    assert cfg.max_payload_tokens == 1000


def test_context_scopes() -> None:
    assert ContextScope.SESSION == "session"
    assert ContextScope.TASK == "task"
    assert ContextScope.OBJECTIVE == "objective"


def test_explorer_summary_creation() -> None:
    s = ExplorerSummary(
        summary="Found 3 relevant files for auth refactor",
        context_files_read=["auth/jwt.py", "auth/session.py"],
        key_symbols=["JWTValidator", "SessionManager"],
        missing_info=["No test coverage data"],
        confidence=0.8,
        suggested_next="Run tests to verify coverage",
    )
    assert len(s.context_files_read) == 2
    assert s.confidence == 0.8


def test_context_event_types() -> None:
    assert ContextEventType.BUDGET_WARNING == "context_budget_warning"
    assert ContextEventType.BUDGET_ENFORCED == "context_budget_enforced"
    assert ContextEventType.ROLLUP_TRIGGERED == "context_rollup_triggered"
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_context_governance_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/context_governance.py`:

```python
"""Context governance schemas.

Defines budget configuration, explorer summary contract, context quality
events, and scope partitioning as specified in orchestrator-context-governance.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ContextScope(StrEnum):
    """Context partition scope."""

    SESSION = "session"
    TASK = "task"
    OBJECTIVE = "objective"


class ContextBudgetConfig(BaseModel):
    """Token budget thresholds for context governance."""

    warning_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    enforcement_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    hard_limit_tokens: int = 1_000_000
    max_payload_tokens: int = 1000
    rollup_oldest_pct: float = Field(default=0.30, ge=0.0, le=1.0)


class ExplorerSummary(BaseModel):
    """Structured summary from Analyst/Researcher to orchestrator.

    The orchestrator receives ONLY this summary, never raw file contents.
    """

    summary: str
    context_files_read: list[str] = Field(default_factory=list)
    key_symbols: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    suggested_next: str = ""


class ContextEventType(StrEnum):
    """Observable context governance events."""

    BUDGET_WARNING = "context_budget_warning"
    BUDGET_ENFORCED = "context_budget_enforced"
    ROLLUP_TRIGGERED = "context_rollup_triggered"
    MEMORY_WINDOW_CREATED = "memory_window_created"
    MEMORY_CONTEXT_LOADED = "memory_context_loaded"
    PAYLOAD_REJECTED = "context_payload_rejected"


class ContextEvent(BaseModel):
    """A trackable context governance event."""

    event_type: ContextEventType
    agent_id: str
    session_id: str
    current_tokens: int = 0
    budget_limit: int = 0
    utilization_pct: float = 0.0
    details: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_context_governance_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/context_governance.py python/tests/test_context_governance_schemas.py
git commit -m "feat(schemas): add context governance budget, explorer summary, and events"
```

---

## Task 2: Context Budget Tracker

**Files:**
- Create: `python/omnimind_backend/orchestrator/context_budget.py`
- Test: `python/tests/test_context_budget.py`

**Step 1: Write the failing test**

Create `python/tests/test_context_budget.py`:

```python
"""Tests for context budget tracking."""

from omnimind_backend.orchestrator.context_budget import ContextBudgetTracker
from omnimind_backend.schemas.context_governance import ContextBudgetConfig, ContextEventType


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
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_context_budget.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/orchestrator/context_budget.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_context_budget.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/orchestrator/context_budget.py python/tests/test_context_budget.py
git commit -m "feat(orchestrator): add context budget tracker with threshold events"
```

---

## Task 3: No-Raw-Context Payload Guard

**Files:**
- Create: `python/omnimind_backend/orchestrator/context_guard.py`
- Test: `python/tests/test_context_guard.py`

**Step 1: Write the failing test**

Create `python/tests/test_context_guard.py`:

```python
"""Tests for no-raw-context payload guard."""

from omnimind_backend.orchestrator.context_guard import validate_payload_size, PayloadTooLargeError


def test_small_payload_passes() -> None:
    payload = "Short summary of findings."
    validate_payload_size(payload)  # Should not raise


def test_large_payload_rejected() -> None:
    import pytest
    payload = "x " * 5000  # ~10000 chars = ~2500 tokens
    with pytest.raises(PayloadTooLargeError):
        validate_payload_size(payload, max_tokens=1000)


def test_custom_max_tokens() -> None:
    payload = "x " * 200  # ~400 chars = ~100 tokens
    validate_payload_size(payload, max_tokens=200)  # Should pass


def test_empty_payload_passes() -> None:
    validate_payload_size("")
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_context_guard.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/orchestrator/context_guard.py`:

```python
"""No-raw-context payload guard.

Rejects oversized payloads from explorer agents (Analyst, Researcher)
before they reach the orchestrator context window.
"""

from __future__ import annotations

_CHARS_PER_TOKEN = 4


class PayloadTooLargeError(ValueError):
    """Raised when a payload exceeds the maximum token limit."""


def estimate_tokens(text: str) -> int:
    """Estimate token count from character length."""
    return len(text) // _CHARS_PER_TOKEN


def validate_payload_size(
    payload: str,
    max_tokens: int = 1000,
) -> None:
    """Reject payloads that exceed the token limit.

    Args:
        payload: Text content to validate.
        max_tokens: Maximum allowed tokens (default: 1000).

    Raises:
        PayloadTooLargeError: If payload exceeds max_tokens.
    """
    tokens = estimate_tokens(payload)
    if tokens > max_tokens:
        raise PayloadTooLargeError(
            f"Payload has ~{tokens} tokens, exceeds limit of {max_tokens}. "
            "Please re-summarize before sending to orchestrator."
        )
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_context_guard.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/orchestrator/context_guard.py python/tests/test_context_guard.py
git commit -m "feat(orchestrator): add no-raw-context payload guard"
```

---

## Task 4: Context Quality Gates

**Files:**
- Create: `python/omnimind_backend/orchestrator/context_quality.py`
- Test: `python/tests/test_context_quality.py`

**Step 1: Write the failing test**

Create `python/tests/test_context_quality.py`:

```python
"""Tests for context quality gates."""

from omnimind_backend.orchestrator.context_quality import (
    check_staleness,
    check_relevance,
    QualityIssue,
)


def test_staleness_recent_ok() -> None:
    issues = check_staleness(current_turn=5, context_turn=4, max_stale_turns=10)
    assert len(issues) == 0


def test_staleness_old_flagged() -> None:
    issues = check_staleness(current_turn=20, context_turn=3, max_stale_turns=10)
    assert len(issues) == 1
    assert issues[0].gate == "staleness"


def test_relevance_high_ok() -> None:
    issues = check_relevance(
        context_topics=["auth", "jwt"],
        task_topics=["auth"],
        min_similarity=0.5,
    )
    assert len(issues) == 0


def test_relevance_low_flagged() -> None:
    issues = check_relevance(
        context_topics=["database", "migration"],
        task_topics=["auth"],
        min_similarity=0.5,
    )
    assert len(issues) == 1
    assert issues[0].gate == "relevance"
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_context_quality.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/orchestrator/context_quality.py`:

```python
"""Context quality gates.

Checks staleness, relevance, and deduplication before the orchestrator
forwards context to an agent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QualityIssue:
    """A quality gate violation."""

    gate: str
    description: str


def check_staleness(
    current_turn: int,
    context_turn: int,
    max_stale_turns: int = 10,
) -> list[QualityIssue]:
    """Flag context older than N turns without refresh."""
    issues: list[QualityIssue] = []
    age = current_turn - context_turn
    if age > max_stale_turns:
        issues.append(QualityIssue(
            gate="staleness",
            description=f"Context is {age} turns old (max {max_stale_turns})",
        ))
    return issues


def check_relevance(
    context_topics: list[str],
    task_topics: list[str],
    min_similarity: float = 0.5,
) -> list[QualityIssue]:
    """Check if context topics relate to current task."""
    issues: list[QualityIssue] = []
    if not task_topics or not context_topics:
        return issues

    ctx_set = {t.lower() for t in context_topics}
    task_set = {t.lower() for t in task_topics}
    overlap = len(ctx_set & task_set)
    similarity = overlap / len(task_set) if task_set else 0.0

    if similarity < min_similarity:
        issues.append(QualityIssue(
            gate="relevance",
            description=f"Topic similarity {similarity:.2f} below threshold {min_similarity}",
        ))
    return issues
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_context_quality.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/orchestrator/context_quality.py python/tests/test_context_quality.py
git commit -m "feat(orchestrator): add context quality gates for staleness and relevance"
```

---

## Task 5: Full Regression Check

**Step 1: Run the full test suite**

Run: `cd python && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Budget config + ExplorerSummary + events | `schemas/context_governance.py` |
| 2 | Budget tracker with threshold events | `orchestrator/context_budget.py` |
| 3 | No-raw-context payload guard | `orchestrator/context_guard.py` |
| 4 | Quality gates (staleness + relevance) | `orchestrator/context_quality.py` |
| 5 | Full regression check | — |
