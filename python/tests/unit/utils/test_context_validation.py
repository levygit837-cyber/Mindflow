"""Tests for context validation and quality gates."""

import pytest

from mindflow_backend.orchestrator.context_validation import (
    validate_payload_size,
    PayloadTooLargeError,
    estimate_tokens,
    check_staleness,
    check_relevance,
    QualityIssue,
    validate_context,
)


def test_small_payload_passes() -> None:
    payload = "Short summary of findings."
    validate_payload_size(payload)  # Should not raise


def test_large_payload_rejected() -> None:
    payload = "x " * 5000  # ~10000 chars = ~2500 tokens
    with pytest.raises(PayloadTooLargeError):
        validate_payload_size(payload, max_tokens=1000)


def test_custom_max_tokens() -> None:
    payload = "x " * 200  # ~400 chars = ~100 tokens
    validate_payload_size(payload, max_tokens=200)  # Should pass


def test_empty_payload_passes() -> None:
    validate_payload_size("")


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("test") == 1  # 4 chars = 1 token
    assert estimate_tokens("test test") == 2  # 9 chars = 2 tokens
    assert estimate_tokens("a" * 100) == 25  # 100 chars = 25 tokens


def test_payload_too_large_error_message() -> None:
    payload = "x " * 2000  # ~4000 chars = ~1000 tokens
    with pytest.raises(PayloadTooLargeError) as exc_info:
        validate_payload_size(payload, max_tokens=500)
    
    error_msg = str(exc_info.value)
    assert "1000 tokens" in error_msg
    assert "exceeds limit of 500" in error_msg
    assert "re-summarize" in error_msg


def test_exact_limit_passes() -> None:
    payload = "x" * 4000  # 4000 chars = 1000 tokens
    validate_payload_size(payload, max_tokens=1000)  # Should pass


def test_one_over_limit_fails() -> None:
    payload = "x " * 4004  # ~4004 chars = ~1001 tokens
    with pytest.raises(PayloadTooLargeError):
        validate_payload_size(payload, max_tokens=1000)


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


def test_validate_context_comprehensive() -> None:
    """Test the comprehensive validation function."""
    # Should pass with no issues
    issues = validate_context(
        payload="Short context",
        current_turn=5,
        context_turn=4,
        context_topics=["auth"],
        task_topics=["auth"],
    )
    assert len(issues) == 0
    
    # Should fail on payload size
    with pytest.raises(PayloadTooLargeError):
        validate_context(
            payload="x " * 5000,  # Large payload
            current_turn=5,
            context_turn=4,
            context_topics=["auth"],
            task_topics=["auth"],
        )
    
    # Should find staleness issue
    issues = validate_context(
        payload="Short context",
        current_turn=20,
        context_turn=3,
        context_topics=["auth"],
        task_topics=["auth"],
        max_stale_turns=10,
    )
    assert len(issues) == 1
    assert issues[0].gate == "staleness"
