"""Tests for context governance schemas."""

from mindflow_backend.schemas.context_governance import (
    ContextBudgetConfig,
    ContextEventType,
    ContextScope,
    ExplorerSummary,
)


def test_budget_config_defaults() -> None:
    cfg = ContextBudgetConfig()
    assert cfg.warning_threshold == 0.80
    assert cfg.enforcement_threshold == 0.90
    assert cfg.hard_limit_tokens == 1_000_000
    assert cfg.max_payload_tokens == 10_000


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