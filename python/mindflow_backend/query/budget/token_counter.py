"""Token budget management — mirrors Claude Code's context budget system.

Adapted from Claude Code's QueryEngine budget management:
- TokenBudget: tracks and enforces context window limits
- TokenUsage: structured token counts
- Automatic trimming when approaching limits

Uses tiktoken for accurate token counting when available, with
character-based estimation as fallback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Rough estimate: ~4 chars per token for typical English/code text
CHARS_PER_TOKEN_ESTIMATE = 4


@dataclass
class TokenUsage:
    """Token usage breakdown by category.

    Mirrors Claude Code's NonNullableUsage structure.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )

    def accumulate(self, other: TokenUsage) -> None:
        """Add another usage to this one (in-place)."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_creation_tokens += other.cache_creation_tokens


@dataclass
class BudgetedContext:
    """A context section with its token count and priority.

    Higher priority sections are kept longer when trimming.
    """

    content: str
    token_count: int
    priority: int  # Higher = more important to keep
    source: str  # Which provider created this section

    @property
    def chars(self) -> int:
        return len(self.content)


class TokenBudget:
    """Manages context window budget for QueryEngine.

    Mirrors Claude Code's budget management:
    - Tracks token usage across all context sources
    - Enforces maximum budget (default: 200,000 tokens for Claude)
    - Provides trimming when approaching limits
    - Uses priority-based trimming (system prompt > recent > older)

    Usage:
        budget = TokenBudget(max_tokens=200_000)
        budget.add_context("system prompt", system_text, priority=100)
        budget.add_context("git status", git_text, priority=50)
        budget.add_context("file content", file_text, priority=10)

        if budget.is_over_budget():
            budget.trim_to_fit()
        assembled = budget.assemble()
    """

    def __init__(
        self,
        max_tokens: int = 200_000,
        warning_threshold: float = 0.8,  # Warn at 80% usage
        use_tiktoken: bool = True,
    ) -> None:
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self._contexts: list[BudgetedContext] = []
        self._total_tokens: int = 0
        self._tiktoken_encoder = None

        if use_tiktoken:
            try:
                import tiktoken

                self._tiktoken_encoder = tiktoken.encoding_for_model("claude-3-5-sonnet-20241022")
            except Exception:
                logger.debug("tiktoken not available, using character estimation")
                self._tiktoken_encoder = None

    def add_context(
        self,
        source: str,
        content: str,
        priority: int = 50,
    ) -> int:
        """Add a context section to the budget.

        Args:
            source: Which provider created this (e.g. "git", "file:main.py")
            content: The actual content text
            priority: Importance (higher = kept longer when trimming)

        Returns:
            Token count of the added section
        """
        token_count = self.count_tokens(content)
        ctx = BudgetedContext(
            content=content,
            token_count=token_count,
            priority=priority,
            source=source,
        )
        self._contexts.append(ctx)
        self._total_tokens += token_count
        return token_count

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken or estimation."""
        if self._tiktoken_encoder:
            return len(self._tiktoken_encoder.encode(text))
        # Fallback: character-based estimation
        return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self._total_tokens)

    @property
    def utilization(self) -> float:
        if self.max_tokens == 0:
            return 0.0
        return self._total_tokens / self.max_tokens

    def is_over_budget(self) -> bool:
        return self._total_tokens > self.max_tokens

    def is_near_limit(self) -> bool:
        return self.utilization >= self.warning_threshold

    def trim_to_fit(self, reserve: int = 10_000) -> list[BudgetedContext]:
        """Trim context sections to fit within budget.

        Trimming strategy (lowest priority first):
        1. Trim low-priority sections entirely
        2. Truncate remaining sections proportionally

        Args:
            reserve: Tokens to reserve for response (default: 10K)

        Returns:
            List of trimmed/removed context sections
        """
        target = self.max_tokens - reserve
        if self._total_tokens <= target:
            return []

        trimmed: list[BudgetedContext] = []

        # Sort by priority (lowest first) then by token count (largest first)
        sorted_ctxs = sorted(
            self._contexts,
            key=lambda c: (c.priority, -c.token_count),
        )

        while self._total_tokens > target and sorted_ctxs:
            # Remove lowest priority section
            removed = sorted_ctxs.pop(0)
            self._contexts.remove(removed)
            self._total_tokens -= removed.token_count
            trimmed.append(removed)

        # If still over budget, truncate remaining sections proportionally
        if self._total_tokens > target:
            ratio = target / self._total_tokens if self._total_tokens > 0 else 0
            for ctx in self._contexts[:]:
                new_tokens = int(ctx.token_count * ratio)
                new_chars = int(len(ctx.content) * ratio)
                if new_tokens < ctx.token_count:
                    ctx.content = ctx.content[:new_chars] + "\n...[truncated]"
                    ctx.token_count = self.count_tokens(ctx.content)
                    self._total_tokens = sum(c.token_count for c in self._contexts)

        if trimmed:
            logger.warning(
                f"Trimmed {len(trimmed)} context sections to fit budget "
                f"({self._total_tokens}/{self.max_tokens} tokens)"
            )

        return trimmed

    def assemble(self, separator: str = "\n\n") -> str:
        """Assemble all context sections into a single string.

        Sections are joined by the separator (default: double newline).
        """
        return separator.join(ctx.content for ctx in self._contexts if ctx.content)

    def get_usage_by_source(self) -> dict[str, int]:
        """Get token usage per source provider."""
        usage: dict[str, int] = {}
        for ctx in self._contexts:
            usage[ctx.source] = usage.get(ctx.source, 0) + ctx.token_count
        return usage

    def reset(self) -> None:
        """Clear all context sections."""
        self._contexts.clear()
        self._total_tokens = 0

    def summary(self) -> dict[str, int]:
        """Get budget summary."""
        return {
            "total_tokens": self._total_tokens,
            "max_tokens": self.max_tokens,
            "remaining_tokens": self.remaining_tokens,
            "utilization_pct": round(self.utilization * 100, 1),
            "sections": len(self._contexts),
        }