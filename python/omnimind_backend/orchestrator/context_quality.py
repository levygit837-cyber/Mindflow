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