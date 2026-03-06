"""Tests for context quality gates."""

from mindflow_backend.orchestrator.context_validation import (
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
    assert "17 turns old" in issues[0].description


def test_staleness_exact_limit_ok() -> None:
    issues = check_staleness(current_turn=15, context_turn=5, max_stale_turns=10)
    assert len(issues) == 0  # Exactly 10 turns is OK


def test_staleness_one_over_limit_flagged() -> None:
    issues = check_staleness(current_turn=16, context_turn=5, max_stale_turns=10)
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
    assert "0.00" in issues[0].description


def test_relevance_partial_overlap() -> None:
    issues = check_relevance(
        context_topics=["auth", "database"],
        task_topics=["auth", "jwt", "session"],
        min_similarity=0.5,
    )
    # Only 1 out of 3 task topics match = 33% < 50%
    assert len(issues) == 1
    assert issues[0].gate == "relevance"


def test_relevance_sufficient_overlap() -> None:
    issues = check_relevance(
        context_topics=["auth", "jwt", "session"],
        task_topics=["auth", "jwt"],
        min_similarity=0.5,
    )
    # 2 out of 2 task topics match = 100% > 50%
    assert len(issues) == 0


def test_relevance_empty_topics() -> None:
    # Empty context topics
    issues = check_relevance(
        context_topics=[],
        task_topics=["auth"],
        min_similarity=0.5,
    )
    assert len(issues) == 0
    
    # Empty task topics
    issues = check_relevance(
        context_topics=["auth"],
        task_topics=[],
        min_similarity=0.5,
    )
    assert len(issues) == 0


def test_relevance_case_insensitive() -> None:
    issues = check_relevance(
        context_topics=["AUTH", "JWT"],
        task_topics=["auth"],
        min_similarity=0.5,
    )
    assert len(issues) == 0  # Should match despite case difference


def test_quality_issue_structure() -> None:
    issues = check_staleness(current_turn=20, context_turn=5, max_stale_turns=10)
    assert len(issues) == 1
    
    issue = issues[0]
    assert isinstance(issue, QualityIssue)
    assert issue.gate == "staleness"
    assert isinstance(issue.description, str)
    assert len(issue.description) > 0