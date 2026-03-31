"""Token Budget Manager for Claude Code-style execution flow.

Inspired by Claude Code's cost-tracker.ts and token budget management.
This module provides:
- Per-session token budget tracking
- Token usage by model
- Budget warnings and limits (hard/soft)
- Cost tracking and formatting
- Auto-compact triggers based on budget thresholds
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage for a single API call."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    model: str = ""
    cost_usd: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.total_tokens == 0:
            self.total_tokens = (
                self.input_tokens
                + self.output_tokens
                + self.cache_creation_tokens
                + self.cache_read_tokens
            )


@dataclass
class TokenBudgetConfig:
    """Configuration for token budget management.

    Inspired by Claude Code's budget system.
    """

    # Hard limit: stop execution when reached
    max_tokens: int = 200_000
    # Soft limit: trigger warning and auto-compact suggestion
    warning_threshold: float = 0.85  # 85% of max_tokens
    # Per-call limit
    max_tokens_per_call: int = 4_000
    # Model-specific limits (override max_tokens for specific models)
    model_limits: dict[str, int] = field(default_factory=dict)
    # Cost limit (USD)
    max_cost_usd: float = 10.0
    # Enable auto-compact when near limit
    auto_compact_enabled: bool = True
    # Auto-compact threshold (0.9 = trigger when 90% used)
    auto_compact_threshold: float = 0.9


class TokenBudgetManager:
    """Manages token budgets, usage tracking, and cost monitoring.

    Inspired by Claude Code's cost-tracker.ts and budget management.

    Usage:
        manager = TokenBudgetManager(session_id="abc123")
        manager.record_usage(TokenUsage(
            input_tokens=1000,
            output_tokens=500,
            model="claude-sonnet-4-20250514",
            cost_usd=0.015
        ))
        if manager.is_over_budget():
            handle_budget_exceeded()
    """

    def __init__(
        self,
        session_id: str = "",
        config: TokenBudgetConfig | None = None,
    ) -> None:
        self.session_id = session_id
        self.config = config or TokenBudgetConfig()
        self._usage_history: list[TokenUsage] = []
        self._total_usage = TokenUsage()
        self._model_usage: dict[str, TokenUsage] = {}
        self._warnings_issued: list[str] = []

    def record_usage(self, usage: TokenUsage) -> None:
        """Record token usage from an API call.

        Args:
            usage: TokenUsage dataclass with token counts and cost.
        """
        self._usage_history.append(usage)

        # Update totals
        self._total_usage.input_tokens += usage.input_tokens
        self._total_usage.output_tokens += usage.output_tokens
        self._total_usage.total_tokens += usage.total_tokens
        self._total_usage.cache_creation_tokens += usage.cache_creation_tokens
        self._total_usage.cache_read_tokens += usage.cache_read_tokens
        self._total_usage.cost_usd += usage.cost_usd

        # Update per-model tracking
        if usage.model not in self._model_usage:
            self._model_usage[usage.model] = TokenUsage(model=usage.model)
        model_usage = self._model_usage[usage.model]
        model_usage.input_tokens += usage.input_tokens
        model_usage.output_tokens += usage.output_tokens
        model_usage.total_tokens += usage.total_tokens
        model_usage.cache_creation_tokens += usage.cache_creation_tokens
        model_usage.cache_read_tokens += usage.cache_read_tokens
        model_usage.cost_usd += usage.cost_usd

        # Check thresholds
        self._check_thresholds()

    def _check_thresholds(self) -> None:
        """Check if any budget thresholds have been crossed."""
        effective_limit = self._get_effective_limit()

        current_ratio = self._total_usage.total_tokens / effective_limit

        # Warning threshold
        if current_ratio >= self.config.warning_threshold:
            warning_key = "budget_warning"
            if warning_key not in self._warnings_issued:
                self._warnings_issued.append(warning_key)
                _logger.warning(
                    "token_budget_warning",
                    session_id=self.session_id,
                    used_tokens=self._total_usage.total_tokens,
                    limit=effective_limit,
                    ratio=current_ratio,
                )

        # Auto-compact trigger
        if (
            self.config.auto_compact_enabled
            and current_ratio >= self.config.auto_compact_threshold
        ):
            _logger.info(
                "token_budget_auto_compact_trigger",
                session_id=self.session_id,
                used_tokens=self._total_usage.total_tokens,
                limit=effective_limit,
                ratio=current_ratio,
            )

    def _get_effective_limit(self) -> int:
        """Get the effective token limit (may vary by model)."""
        # For now, use base config limit
        return self.config.max_tokens

    def is_over_budget(self) -> bool:
        """Check if the current session has exceeded its token budget."""
        return self._total_usage.total_tokens >= self.config.max_tokens

    def is_over_cost_budget(self) -> bool:
        """Check if the current session has exceeded its cost budget."""
        return self._total_usage.cost_usd >= self.config.max_cost_usd

    def should_compact(self) -> bool:
        """Check if auto-compact should be triggered."""
        if not self.config.auto_compact_enabled:
            return False
        effective_limit = self._get_effective_limit()
        return (
            self._total_usage.total_tokens
            >= effective_limit * self.config.auto_compact_threshold
        )

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status as a dictionary."""
        effective_limit = self._get_effective_limit()
        current = self._total_usage.total_tokens
        ratio = current / effective_limit if effective_limit > 0 else 0

        return {
            "session_id": self.session_id,
            "total_tokens_used": current,
            "total_cost_usd": self._total_usage.cost_usd,
            "input_tokens": self._total_usage.input_tokens,
            "output_tokens": self._total_usage.output_tokens,
            "cache_tokens": (
                self._total_usage.cache_creation_tokens
                + self._total_usage.cache_read_tokens
            ),
            "token_limit": effective_limit,
            "token_ratio": round(ratio, 3),
            "remaining_tokens": max(0, effective_limit - current),
            "cost_limit": self.config.max_cost_usd,
            "is_over_budget": self.is_over_budget(),
            "is_over_cost_budget": self.is_over_cost_budget(),
            "should_compact": self.should_compact(),
            "warnings_issued": list(self._warnings_issued),
            "model_usage": {
                model: {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                    "cost_usd": round(usage.cost_usd, 4),
                }
                for model, usage in self._model_usage.items()
            },
        }

    def get_usage_history(self) -> list[TokenUsage]:
        """Get the full usage history."""
        return list(self._usage_history)

    def get_model_usage(self, model: str) -> TokenUsage | None:
        """Get usage for a specific model."""
        return self._model_usage.get(model)

    def reset(self) -> None:
        """Reset all budget tracking (for session restart)."""
        self._usage_history.clear()
        self._total_usage = TokenUsage()
        self._model_usage.clear()
        self._warnings_issued.clear()

    @staticmethod
    def format_token_count(tokens: int) -> str:
        """Format token count for display (e.g., '1.2K', '1.5M')."""
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1_000:
            return f"{tokens / 1_000:.1f}K"
        return str(tokens)

    @staticmethod
    def format_cost(cost_usd: float) -> str:
        """Format cost for display (e.g., '$0.015')."""
        if cost_usd >= 1.0:
            return f"${cost_usd:.2f}"
        return f"${cost_usd:.4f}"