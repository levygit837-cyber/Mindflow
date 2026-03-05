"""Context validation and quality gates.

Combines functionality from context_guard.py and context_quality.py
to provide comprehensive context validation including staleness checks,
relevance validation, and payload size limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

_CHARS_PER_TOKEN = 4


@dataclass
class QualityIssue:
    """A quality gate violation."""

    gate: str
    description: str


class PayloadTooLargeError(ValueError):
    """Raised when a payload exceeds maximum token limit."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def estimate_tokens(text: str) -> int:
    """Estimate token count from character length."""
    return len(text) // _CHARS_PER_TOKEN


def validate_payload_size(
    payload: str,
    max_tokens: int = 1000,
) -> None:
    """Reject payloads that exceed token limit.

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


def check_staleness(
    current_turn: int,
    context_turn: int,
    max_stale_turns: int = 10,
) -> List[QualityIssue]:
    """Flag context older than N turns without refresh."""
    issues: List[QualityIssue] = []
    age = current_turn - context_turn
    if age > max_stale_turns:
        issues.append(QualityIssue(
            gate="staleness",
            description=f"Context is {age} turns old (max {max_stale_turns})",
        ))
    return issues


def check_relevance(
    context_topics: List[str],
    task_topics: List[str],
    min_similarity: float = 0.5,
) -> List[QualityIssue]:
    """Check if context topics relate to current task."""
    issues: List[QualityIssue] = []
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


def validate_context(
    payload: str,
    current_turn: int,
    context_turn: int,
    context_topics: List[str],
    task_topics: List[str],
    max_tokens: int = 1000,
    max_stale_turns: int = 10,
    min_similarity: float = 0.5,
) -> List[QualityIssue]:
    """Comprehensive context validation.
    
    Combines payload size validation with quality gates.
    
    Args:
        payload: Text content to validate
        current_turn: Current conversation turn
        context_turn: Turn when context was generated
        context_topics: Topics in the context
        task_topics: Topics relevant to current task
        max_tokens: Maximum allowed tokens
        max_stale_turns: Maximum age in turns
        min_similarity: Minimum topic similarity
        
    Returns:
        List of quality issues found
        
    Raises:
        PayloadTooLargeError: If payload exceeds max_tokens
    """
    # Check payload size first
    validate_payload_size(payload, max_tokens)
    
    # Check quality gates
    issues = []
    issues.extend(check_staleness(current_turn, context_turn, max_stale_turns))
    issues.extend(check_relevance(context_topics, task_topics, min_similarity))
    
    return issues
