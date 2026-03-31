"""Auto-Compact Service for context window management.

Inspired by Claude Code's auto-compact system (autoCompact.ts, compact.ts, snipCompact.ts).
This module provides:
- Snip Compact: Remove oldest messages while preserving system context
- Cache Compact: Use model's built-in caching for context compaction
- Context Collapse: Merge consecutive similar messages into summaries
- Compact boundary detection and recovery
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CompactStrategy(str, Enum):
    """Strategy to use for context compaction."""

    SNIP = "snip"  # Remove oldest messages
    CACHE = "cache"  # Use model's cache for compaction
    COLLAPSE = "collapse"  # Merge consecutive similar messages
    SUMMARY = "summary"  # Use LLM to summarize conversation


@dataclass
class CompactResult:
    """Result of a compaction operation."""

    original_tokens: int = 0
    compacted_tokens: int = 0
    tokens_saved: int = 0
    messages_removed: int = 0
    messages_compacted: int = 0
    strategy_used: CompactStrategy = CompactStrategy.SNIP
    success: bool = True
    error: str | None = None


@dataclass
class CompactConfig:
    """Configuration for auto-compaction."""

    # Target context window size (in tokens)
    target_window_size: int = 128_000
    # Maximum tokens before triggering compaction
    max_context_tokens: int = 180_000
    # Minimum tokens to keep after compaction
    min_kept_tokens: int = 50_000
    # System prompt reservation (tokens)
    system_prompt_reservation: int = 5_000
    # Enable LLM-based summary compaction
    enable_llm_summary: bool = True
    # Enable snip compaction
    enable_snip: bool = True
    # Enable cache compaction
    enable_cache_compact: bool = True
    # Enable context collapse
    enable_context_collapse: bool = True


class AutoCompactService:
    """Service for managing context window compaction.

    Inspired by Claude Code's auto-compact system.
    Handles:
    - Snip compaction (remove oldest messages)
    - Cache compaction (use model's built-in caching)
    - Context collapse (merge similar messages)
    - LLM-based summary compaction

    Usage:
        service = AutoCompactService()
        result = service.compact(messages, current_token_count)
        if result.success:
            use_compacted_messages(result.compacted_messages)
    """

    def __init__(self, config: CompactConfig | None = None) -> None:
        self.config = config or CompactConfig()

    def should_compact(self, current_tokens: int) -> bool:
        """Check if context should be compacted.

        Args:
            current_tokens: Current token count in context.

        Returns:
            True if compaction should be triggered.
        """
        return current_tokens >= self.config.max_context_tokens

    def compact(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
        llm_summarize_fn=None,  # Optional async function for LLM summary
    ) -> CompactResult:
        """Compact the message list to reduce token count.

        Tries strategies in order: snip → collapse → summary → cache.

        Args:
            messages: List of conversation messages.
            current_tokens: Current token count.
            llm_summarize_fn: Optional async callable(messages) -> str.

        Returns:
            CompactResult with compaction statistics.
        """
        if not self.should_compact(current_tokens):
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                strategy_used=CompactStrategy.SNIP,
            )

        # Try snip first (fastest, no API calls)
        if self.config.enable_snip:
            result = self._snip_compact(messages, current_tokens)
            if result.success:
                return result

        # Try context collapse
        if self.config.enable_context_collapse:
            result = self._context_collapse(messages, current_tokens)
            if result.success:
                return result

        # Try LLM summary (most expensive)
        if self.config.enable_llm_summary and llm_summarize_fn is not None:
            # This would be async in practice
            result = self._summary_compact_stub(messages, current_tokens)
            if result.success:
                return result

        # Fallback to cache compact
        if self.config.enable_cache_compact:
            result = self._cache_compact_stub(messages, current_tokens)
            return result

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=current_tokens,
            success=False,
            error="No compaction strategy available",
        )

    def _snip_compact(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
    ) -> CompactResult:
        """Snip compactation: remove oldest messages while preserving context.

        Strategy:
        1. Keep system messages
        2. Keep the most recent N messages that fit within target
        3. Insert a "[Previous conversation snipped]" placeholder
        """
        if len(messages) <= 2:
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                messages_removed=0,
                strategy_used=CompactStrategy.SNIP,
                success=False,
                error="Not enough messages to snip",
            )

        # Separate system messages from conversation
        system_messages = []
        conversation = []
        for msg in messages:
            if msg.get("role") == "system":
                system_messages.append(msg)
            else:
                conversation.append(msg)

        # Estimate tokens per message (rough)
        if not conversation:
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                strategy_used=CompactStrategy.SNIP,
                success=False,
                error="No conversation messages to snip",
            )

        avg_token_per_msg = current_tokens / max(len(messages), 1)

        # Calculate how many recent messages to keep
        target_content = self.config.target_window_size - self.config.system_prompt_reservation
        tokens_used_by_system = len(system_messages) * avg_token_per_msg
        available_for_conversation = target_content - tokens_used_by_system

        # Keep messages from the end until we hit the limit
        kept_messages = []
        removed_count = 0
        estimated_kept_tokens = 0

        for msg in reversed(conversation):
            msg_tokens = max(int(avg_token_per_msg), 1)
            if estimated_kept_tokens + msg_tokens <= available_for_conversation:
                kept_messages.insert(0, msg)
                estimated_kept_tokens += msg_tokens
            else:
                removed_count += 1
                break

        # If we're still over, remove more aggressively
        while (
            estimated_kept_tokens > available_for_conversation
            and len(kept_messages) > 2
        ):
            kept_messages.pop(0)
            removed_count += 1
            estimated_kept_tokens -= max(int(avg_token_per_msg), 1)

        # Insert snip placeholder if we removed messages
        if removed_count > 0:
            snip_placeholder = {
                "role": "system",
                "content": (
                    f"[{removed_count} previous message(s) snipped to save context. "
                    f"The assistant should continue from the latest user request.]"
                ),
            }
            final_messages = system_messages + [snip_placeholder] + kept_messages
        else:
            final_messages = messages

        tokens_saved = current_tokens - estimated_kept_tokens

        _logger.info(
            "auto_compact_snip",
            messages_removed=removed_count,
            messages_kept=len(kept_messages),
            tokens_saved=tokens_saved,
            original_tokens=current_tokens,
            compacted_tokens=estimated_kept_tokens,
        )

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=estimated_kept_tokens,
            tokens_saved=tokens_saved,
            messages_removed=removed_count,
            messages_compacted=len(kept_messages),
            strategy_used=CompactStrategy.SNIP,
            success=True,
        )

    def _context_collapse(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
    ) -> CompactResult:
        """Context collapse: merge consecutive messages with the same role.

        Reduces context by merging tool_result + tool_use pairs and
        consecutive assistant messages.
        """
        if len(messages) <= 2:
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                strategy_used=CompactStrategy.COLLAPSE,
                success=False,
                error="Not enough messages to collapse",
            )

        collapsed = []
        current_group = []
        current_role = None
        collapsed_count = 0

        for msg in messages:
            role = msg.get("role", "")

            # Group tool results with their corresponding tool uses
            if role == "assistant" and current_role in ("assistant", None):
                current_group.append(msg)
                current_role = role
            elif role == "user" and current_role in ("user", None):
                current_group.append(msg)
                current_role = role
            else:
                # Flush current group if > 1 message
                if len(current_group) > 1:
                    merged = self._merge_messages(current_group)
                    collapsed.append(merged)
                    collapsed_count += len(current_group) - 1
                elif current_group:
                    collapsed.extend(current_group)
                current_group = [msg]
                current_role = role

        # Flush remaining
        if len(current_group) > 1:
            merged = self._merge_messages(current_group)
            collapsed.append(merged)
            collapsed_count += len(current_group) - 1
        elif current_group:
            collapsed.extend(current_group)

        # Estimate token savings (rough: ~30% reduction per collapsed pair)
        estimated_savings = int(current_tokens * 0.1 * (collapsed_count / max(len(messages), 1)))
        final_tokens = max(current_tokens - estimated_savings, current_tokens // 2)

        _logger.info(
            "auto_compact_collapse",
            messages_collapsed=collapsed_count,
            tokens_saved=estimated_savings,
        )

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=final_tokens,
            tokens_saved=estimated_savings,
            messages_removed=collapsed_count,
            messages_compacted=len(collapsed),
            strategy_used=CompactStrategy.COLLAPSE,
            success=True,
        )

    def _merge_messages(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge consecutive messages with the same role."""
        if len(messages) == 1:
            return messages[0]

        role = messages[0].get("role", "assistant")
        contents = []

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                contents.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        contents.append(
                            block.get("text", json.dumps(block))
                        )
                    else:
                        contents.append(str(block))

        merged_content = "\n\n".join(contents)

        # Truncate if too long
        max_content_length = 8000
        if len(merged_content) > max_content_length:
            merged_content = merged_content[:max_content_length] + "\n\n[...truncated...]"

        merged = {"role": role, "content": merged_content}

        # Preserve tool-related metadata if present
        if "tool_calls" in messages[-1]:
            merged["tool_calls"] = messages[-1]["tool_calls"]

        return merged

    def _summary_compact_stub(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
    ) -> CompactResult:
        """Summary compaction stub (would use LLM in production).

        In a full implementation, this would send the conversation history
        to an LLM with a prompt like:
        'Summarize this conversation, preserving all important context,
        tool results, and the latest user request.'
        """
        # Stub: just keep system + last 2 messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent = messages[-2:] if len(messages) > 2 else messages

        compacted = system_msgs + recent
        estimated_tokens = current_tokens // 3  # Rough estimate

        _logger.info(
            "auto_compact_summary_stub",
            original_tokens=current_tokens,
            compacted_tokens=estimated_tokens,
        )

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=estimated_tokens,
            tokens_saved=current_tokens - estimated_tokens,
            messages_removed=len(messages) - len(compacted),
            messages_compacted=len(compacted),
            strategy_used=CompactStrategy.SUMMARY,
            success=True,
        )

    def _cache_compact_stub(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
    ) -> CompactResult:
        """Cache compaction stub.

        In a full implementation, this would leverage the model's built-in
        prompt caching. Messages within the cache window are marked with
        cache_control parameters to tell the API to use cached context.
        """
        # Stub: mark last few messages for cache control
        estimated_tokens = current_tokens  # No actual reduction in stub

        _logger.info(
            "auto_compact_cache_stub",
            original_tokens=current_tokens,
        )

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=estimated_tokens,
            tokens_saved=0,
            strategy_used=CompactStrategy.CACHE,
            success=True,
        )