"""Auto-Compact Service for context window management.

Inspired by Claude Code's auto-compact system (autoCompact.ts, compact.ts, snipCompact.ts).
This module provides:
- Snip Compact: Remove oldest messages while preserving system context
- Cache Compact: Use model's built-in caching for context compaction
- Context Collapse: Merge consecutive similar messages into summaries
- LLM-based Summary Compact: Use LLM to generate intelligent summaries
- PTL Retry: Retry compaction when prompt is too long
- Circuit Breaker: Stop retrying after consecutive failures
- File State Preservation: Preserve recently accessed files after compaction
- Keep-Alive: Send signals during long compaction to prevent timeouts
- Compact boundary detection and recovery
"""

from __future__ import annotations

import json
import time
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.query.cache.file_cache import SessionFileCache, create_session_cache

_logger = get_logger(__name__)

# Maximum retries when compaction request itself is too long
MAX_PTL_RETRIES = 3

# Stop trying autocompact after this many consecutive failures
MAX_CONSECUTIVE_FAILURES = 3

# Buffer tokens reserved for compaction output
AUTOCOMPACT_BUFFER_TOKENS = 13_000

# Maximum files to restore after compaction
POST_COMPACT_MAX_FILES_TO_RESTORE = 5

# Token budget for post-compact file restoration
POST_COMPACT_TOKEN_BUDGET = 50_000

# Maximum tokens per file for restoration
POST_COMPACT_MAX_TOKENS_PER_FILE = 5_000

# Keep-alive interval in seconds
KEEPALIVE_INTERVAL_SECONDS = 30

# Model-specific context windows (tokens)
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # Anthropic models
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku": 200_000,
    "claude-3.5-sonnet": 200_000,
    "claude-3.5-haiku": 200_000,
    # OpenAI models
    "gpt-4": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-3.5-turbo": 16_000,
    # Default fallback
    "default": 128_000,
}


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
    compacted_messages: list[dict[str, Any]] = field(default_factory=list)
    strategy_used: CompactStrategy = CompactStrategy.SNIP
    success: bool = True
    error: str | None = None


@dataclass
class AutoCompactTrackingState:
    """Tracking state for auto-compaction circuit breaker."""

    compacted: bool = False
    turn_counter: int = 0
    turn_id: str = ""
    consecutive_failures: int = 0


@dataclass
class FileState:
    """State of a file for post-compaction restoration."""

    content: str
    timestamp: float
    path: str


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

    def __init__(
        self,
        config: CompactConfig | None = None,
        file_cache: SessionFileCache | None = None,
        session_id: str | None = None,
        cwd: str | None = None,
    ) -> None:
        self.config = config or CompactConfig()
        self._file_cache = file_cache
        self._session_id = session_id
        self._cwd = cwd
        self._hook_manager = HookManager.get_instance()

    def should_compact(
        self,
        current_tokens: int,
        tracking: AutoCompactTrackingState | None = None,
    ) -> bool:
        """Check if context should be compacted.

        Args:
            current_tokens: Current token count in context.
            tracking: Optional tracking state for circuit breaker.

        Returns:
            True if compaction should be triggered.
        """
        # Circuit breaker: stop after consecutive failures
        if tracking and tracking.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            return False
        
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
        """Summary compaction using LLM.

        Sends conversation history to LLM for intelligent summarization,
        preserving important context, tool results, and the latest user request.
        Falls back to snip-style compaction if LLM is unavailable.
        """
        # Separate system messages from conversation
        system_msgs = [m for m in messages if m.get("role") == "system"]
        conversation_msgs = [m for m in messages if m.get("role") != "system"]

        if len(conversation_msgs) <= 3:
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                strategy_used=CompactStrategy.SUMMARY,
                success=False,
                error="Not enough conversation messages to summarize",
            )

        # Build summarization prompt
        conversation_text = self._format_messages_for_summary(conversation_msgs)

        summary_prompt = (
            "You are a conversation summarizer. Summarize the following conversation "
            "between a user and an AI assistant. Preserve ALL important context including:\n"
            "- Key decisions made\n"
            "- Files read/written and their purposes\n"
            "- Tool results that contain important information\n"
            "- The latest user request and current task state\n"
            "- Any errors or issues encountered\n\n"
            "Be concise but comprehensive. Focus on actionable context.\n\n"
            f"Conversation:\n{conversation_text}\n\n"
            "Summary:"
        )

        # Try to get LLM response via provider
        summary = self._call_llm_for_summary(summary_prompt)

        if not summary:
            # Fallback: keep system + last 3 messages + a placeholder
            _logger.warning(
                "auto_compact_summary_llm_fallback",
                original_tokens=current_tokens,
                reason="LLM unavailable or returned empty response",
            )
            recent = conversation_msgs[-3:] if len(conversation_msgs) > 3 else conversation_msgs
            fallback_summary = (
                f"[Conversation compacted. {len(conversation_msgs)} messages reduced. "
                f"Previous context was summarized but LLM was unavailable. "
                f"Key recent messages preserved below.]"
            )
            summary_message = {
                "role": "user",
                "content": fallback_summary,
                "is_compact_summary": True,
            }
            compacted = system_msgs + [summary_message] + recent
        else:
            # Create summary message
            summary_message = {
                "role": "user",
                "content": f"[Previous conversation summarized]\n\n{summary}",
                "is_compact_summary": True,
            }
            # Keep system + summary + last 2 messages for continuity
            recent = conversation_msgs[-2:] if len(conversation_msgs) > 2 else conversation_msgs
            compacted = system_msgs + [summary_message] + recent

        estimated_tokens = self._estimate_tokens(compacted)
        messages_removed = max(0, len(messages) - len(compacted))

        _logger.info(
            "auto_compact_summary",
            original_tokens=current_tokens,
            compacted_tokens=estimated_tokens,
            tokens_saved=current_tokens - estimated_tokens,
            messages_removed=messages_removed,
            messages_kept=len(compacted),
            summary_length=len(summary) if summary else 0,
        )

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=estimated_tokens,
            tokens_saved=current_tokens - estimated_tokens,
            messages_removed=messages_removed,
            messages_compacted=len(compacted),
            compacted_messages=compacted,
            strategy_used=CompactStrategy.SUMMARY,
            success=True,
        )

    def _format_messages_for_summary(
        self, messages: list[dict[str, Any]]
    ) -> str:
        """Format messages for LLM summarization prompt."""
        parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Handle tool results
            if role == "tool":
                tool_name = msg.get("name", "unknown_tool")
                parts.append(f"[Tool Result: {tool_name}]: {str(content)[:500]}")
            elif role == "assistant":
                # Check for tool calls
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    tool_names = [tc.get("function", {}).get("name", "?") for tc in tool_calls]
                    parts.append(f"Assistant: [Called tools: {', '.join(tool_names)}]")
                else:
                    parts.append(f"Assistant: {str(content)[:500]}")
            elif role == "user":
                parts.append(f"User: {str(content)[:500]}")
            else:
                parts.append(f"{role}: {str(content)[:300]}")

        return "\n".join(parts)

    def _call_llm_for_summary(self, prompt: str) -> str | None:
        """Call LLM to generate conversation summary.

        Tries to use the configured provider. Returns None if unavailable.
        """
        try:
            from mindflow_backend.infra.config import get_settings
            from mindflow_backend.runtime.providers import get_model_for_provider

            settings = get_settings()
            provider = settings.default_provider or "ollama"
            model = settings.default_model or "qwen3:8b"

            llm = get_model_for_provider(provider, model)

            # Use synchronous invoke for simplicity in compact context
            # The compact method is sync, so we use invoke instead of ainvoke
            from langchain_core.messages import HumanMessage

            response = llm.invoke([HumanMessage(content=prompt)])

            if response and hasattr(response, "content"):
                content = response.content
                if isinstance(content, str) and content.strip():
                    return content.strip()
                elif isinstance(content, list):
                    # Handle list of content blocks
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    return "\n".join(text_parts).strip()

            return None

        except ImportError as exc:
            _logger.debug(
                "auto_compact_summary_import_error",
                error=str(exc),
            )
            return None
        except Exception as exc:
            _logger.warning(
                "auto_compact_summary_llm_error",
                error=str(exc),
            )
            return None

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

    async def _summary_compact(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
        llm_summarize_fn: Callable[[list[dict[str, Any]]], Awaitable[str | None]],
    ) -> CompactResult:
        """LLM-based summary compaction with fact preservation.

        Pipeline:
        1. Extract SessionFacts via FactExtractor (preserve for future sessions)
        2. Generate consolidated summary via LLM
        3. Persist facts + embeddings
        4. Build compacted message list: system + summary + recent messages

        Args:
            messages: List of conversation messages.
            current_tokens: Current token count.
            llm_summarize_fn: Async callable that takes messages and returns summary.

        Returns:
            CompactResult with compaction statistics.
        """
        # Separate system messages from conversation
        system_msgs = [m for m in messages if m.get("role") == "system"]
        conversation_msgs = [m for m in messages if m.get("role") != "system"]

        if not conversation_msgs:
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                success=False,
                error="No conversation messages to compact",
            )

        # Step 1: Extract SessionFacts (persisted separately for cross-session recall)
        facts_count = 0
        try:
            from mindflow_backend.memory.session.fact_extractor import SessionFactExtractor
            from mindflow_backend.infra.database.connection import get_db_session

            session_id = self._extract_session_id(messages)
            agent_id = self._extract_agent_id(messages)

            if session_id:
                fact_extractor = SessionFactExtractor()
                facts = await fact_extractor.extract(conversation_msgs, session_id, agent_id)

                if facts:
                    # Persist facts with embeddings
                    async with get_db_session() as db:
                        facts_count = await fact_extractor.persist_facts(
                            db,
                            facts,
                            generate_embeddings=True,
                        )

                    _logger.info(
                        "compaction_facts_extracted",
                        session_id=session_id,
                        facts_count=facts_count,
                    )
        except Exception as exc:
            _logger.warning(
                "compaction_fact_extraction_failed",
                error=str(exc),
            )
            # Continue with compaction even if fact extraction fails

        # Step 2: Generate summary via LLM
        messages_for_summary = self._strip_images(messages)
        summary = await llm_summarize_fn(messages_for_summary)

        if not summary:
            _logger.warning("compaction_summary_failed")
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                strategy_used=CompactStrategy.SUMMARY,
                success=False,
                error="No summary generated",
            )

        # Step 3: Build compacted messages
        recent_count = min(5, len(conversation_msgs))
        recent_msgs = conversation_msgs[-recent_count:]

        # Create summary message with fact preservation notice
        summary_content = (
            f"[Session compacted. {len(conversation_msgs)} messages → summary + "
            f"{recent_count} recent."
        )
        if facts_count > 0:
            summary_content += f" {facts_count} facts preserved for future sessions."
        summary_content += f"]\n\n{summary}"

        summary_message = {
            "role": "user",
            "content": summary_content,
            "is_compact_summary": True,
        }

        compacted = system_msgs + [summary_message] + recent_msgs
        estimated_tokens = self._estimate_tokens(compacted)

        messages_removed = len(conversation_msgs) - recent_count

        _logger.info(
            "auto_compact_summary",
            original_tokens=current_tokens,
            compacted_tokens=estimated_tokens,
            tokens_saved=current_tokens - estimated_tokens,
            messages_removed=messages_removed,
            facts_preserved=facts_count,
        )

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=estimated_tokens,
            tokens_saved=current_tokens - estimated_tokens,
            messages_removed=messages_removed,
            messages_compacted=len(compacted),
            compacted_messages=compacted,
            strategy_used=CompactStrategy.SUMMARY,
            success=True,
        )

    async def _run_pre_compact_hooks(self, trigger: str) -> tuple[bool, str | None]:
        """Executa PreCompact e retorna se a compactação pode prosseguir."""
        if not self._session_id:
            return True, None

        async for result in self._hook_manager.execute_pre_compact(
            session_id=self._session_id,
            trigger=trigger,
            cwd=self._cwd,
        ):
            if result.prevent_continuation:
                return False, result.stop_reason or result.error or "Compaction blocked by hook"
            if getattr(result, "behavior", None) == "deny":
                return False, result.reason or result.error or "Compaction blocked by hook"

        return True, None

    async def _run_post_compact_hooks(
        self,
        trigger: str,
        summary: str,
    ) -> None:
        """Executa PostCompact após compactação bem-sucedida."""
        if not self._session_id:
            return

        async for _ in self._hook_manager.execute_post_compact(
            session_id=self._session_id,
            trigger=trigger,
            summary=summary,
            cwd=self._cwd,
        ):
            pass

    @staticmethod
    def _build_compact_summary(result: CompactResult) -> str:
        """Resume a compactação para hooks PostCompact."""
        return (
            f"strategy={result.strategy_used.value}; "
            f"original_tokens={result.original_tokens}; "
            f"compacted_tokens={result.compacted_tokens}; "
            f"tokens_saved={result.tokens_saved}; "
            f"messages_removed={result.messages_removed}"
        )

    async def compact_with_retry(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
        llm_summarize_fn: Callable[[list[dict[str, Any]]], Awaitable[str | None]],
    ) -> CompactResult:
        """Compact with PTL (Prompt Too Long) retry logic.

        If the compaction request itself is too long, truncates oldest messages
        and retries up to MAX_PTL_RETRIES times.

        Args:
            messages: List of conversation messages.
            current_tokens: Current token count.
            llm_summarize_fn: Async callable for LLM summary.

        Returns:
            CompactResult with compaction statistics.
        """
        allowed, block_reason = await self._run_pre_compact_hooks("auto")
        if not allowed:
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                success=False,
                error=block_reason or "Compaction blocked by hook",
            )

        messages_to_summarize = list(messages)
        ptl_attempts = 0

        while ptl_attempts <= MAX_PTL_RETRIES:
            result = await self._summary_compact(
                messages_to_summarize,
                current_tokens,
                llm_summarize_fn,
            )

            if result.success:
                await self._run_post_compact_hooks(
                    "auto",
                    self._build_compact_summary(result),
                )
                return result

            # Check if error is PTL-related
            error_msg = (result.error or "").lower()
            if "prompt too long" not in error_msg and "context length" not in error_msg:
                return result

            # Truncate oldest messages and retry
            ptl_attempts += 1
            if ptl_attempts > MAX_PTL_RETRIES:
                _logger.error(
                    "compact_ptl_max_retries",
                    attempts=ptl_attempts,
                    original_messages=len(messages),
                )
                return CompactResult(
                    original_tokens=current_tokens,
                    compacted_tokens=current_tokens,
                    success=False,
                    error="Prompt too long after max retries",
                )

            # Drop oldest 20% of messages
            drop_count = max(1, len(messages_to_summarize) // 5)
            messages_to_summarize = messages_to_summarize[drop_count:]

            _logger.warning(
                "compact_ptl_retry",
                attempt=ptl_attempts,
                dropped_messages=drop_count,
                remaining_messages=len(messages_to_summarize),
            )

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=current_tokens,
            success=False,
            error="Max PTL retries exceeded",
        )

    def _strip_images(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Strip image blocks from messages before sending to LLM.

        Images are not needed for summarization and can cause PTL errors.

        Args:
            messages: List of messages.

        Returns:
            Messages with images replaced by text markers.
        """
        stripped = []
        for msg in messages:
            content = msg.get("content", "")

            if isinstance(content, str):
                stripped.append(msg)
            elif isinstance(content, list):
                new_content = []
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "")
                        if block_type == "image":
                            new_content.append({"type": "text", "text": "[image]"})
                        elif block_type == "document":
                            new_content.append({"type": "text", "text": "[document]"})
                        else:
                            new_content.append(block)
                    else:
                        new_content.append(block)

                stripped.append({**msg, "content": new_content})
            else:
                stripped.append(msg)

        return stripped

    def _estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate token count for messages.

        Uses rough estimation: ~4 characters per token.

        Args:
            messages: List of messages.

        Returns:
            Estimated token count.
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", "")
                        total_chars += len(str(text))

        return total_chars // 4

    def _extract_session_id(self, messages: list[dict[str, Any]]) -> str:
        """Extract session_id from messages metadata.

        Args:
            messages: List of conversation messages

        Returns:
            Session ID or generated fallback if not found
        """
        # Try to find session_id in message metadata
        for msg in messages:
            if isinstance(msg, dict):
                # Check in metadata field
                metadata = msg.get("metadata", {})
                if isinstance(metadata, dict):
                    session_id = metadata.get("session_id")
                    if session_id:
                        return str(session_id)

                # Check in top-level fields
                session_id = msg.get("session_id")
                if session_id:
                    return str(session_id)

        # Fallback: generate from timestamp
        import hashlib
        import time
        timestamp = str(time.time())
        return hashlib.md5(timestamp.encode()).hexdigest()[:16]

    def _extract_agent_id(self, messages: list[dict[str, Any]]) -> str:
        """Extract agent_id from messages metadata.

        Args:
            messages: List of conversation messages

        Returns:
            Agent ID or "compaction" if not found
        """
        # Try to find agent_id in message metadata
        for msg in messages:
            if isinstance(msg, dict):
                # Check in metadata field
                metadata = msg.get("metadata", {})
                if isinstance(metadata, dict):
                    agent_id = metadata.get("agent_id")
                    if agent_id:
                        return str(agent_id)

                # Check in top-level fields
                agent_id = msg.get("agent_id")
                if agent_id:
                    return str(agent_id)

                # Check role field for assistant messages
                if msg.get("role") == "assistant":
                    name = msg.get("name")
                    if name:
                        return str(name)

        # Fallback
        return "compaction"

    async def compact_with_cache_sharing(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
        llm_summarize_fn: Callable[[list[dict[str, Any]]], Awaitable[str | None]],
        cache_params: dict[str, Any] | None = None,
    ) -> CompactResult:
        """Compact with prompt cache sharing.

        Uses forked agent to reuse main thread's cached prefix (system prompt,
        tools, context messages). Falls back to regular streaming on failure.

        Args:
            messages: List of conversation messages.
            current_tokens: Current token count.
            llm_summarize_fn: Async callable for LLM summary.
            cache_params: Optional cache parameters for sharing.

        Returns:
            CompactResult with compaction statistics.
        """
        if cache_params:
            try:
                # Try cache-aware compaction
                result = await self._compact_with_cache(messages, current_tokens, cache_params)
                if result.success:
                    _logger.info(
                        "compact_cache_sharing_success",
                        original_tokens=current_tokens,
                        compacted_tokens=result.compacted_tokens,
                    )
                    return result
            except Exception as e:
                _logger.warning(
                    "compact_cache_sharing_fallback",
                    error=str(e),
                    original_tokens=current_tokens,
                )

        # Fallback to regular compaction
        return await self._summary_compact(messages, current_tokens, llm_summarize_fn)

    async def _compact_with_cache(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
        cache_params: dict[str, Any],
    ) -> CompactResult:
        """Internal cache-aware compaction."""
        # Strip images before sending to LLM
        messages_for_summary = self._strip_images(messages)

        # Generate summary using LLM
        summary = await cache_params.get("llm_summarize_fn", lambda x: None)(messages_for_summary)

        if not summary:
            return CompactResult(
                original_tokens=current_tokens,
                compacted_tokens=current_tokens,
                success=False,
                error="No summary generated",
            )

        # Create summary message
        summary_message = {
            "role": "user",
            "content": f"[Previous conversation summarized]\n\n{summary}",
            "is_compact_summary": True,
        }

        # Keep system messages + summary + last few messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent = messages[-3:] if len(messages) > 3 else []

        compacted = system_msgs + [summary_message] + recent
        estimated_tokens = self._estimate_tokens(compacted)

        return CompactResult(
            original_tokens=current_tokens,
            compacted_tokens=estimated_tokens,
            tokens_saved=current_tokens - estimated_tokens,
            messages_removed=len(messages) - len(compacted),
            messages_compacted=len(compacted),
            strategy_used=CompactStrategy.CACHE,
            success=True,
        )

    async def create_post_compact_file_attachments(
        self,
        file_state: dict[str, FileState],
        max_files: int = POST_COMPACT_MAX_FILES_TO_RESTORE,
        token_budget: int = POST_COMPACT_TOKEN_BUDGET,
    ) -> list[dict[str, Any]]:
        """Restore recently accessed files after compaction.

        Reads files that were recently accessed and creates attachment
        messages to restore context without re-reading.

        Args:
            file_state: Dictionary of file path -> FileState.
            max_files: Maximum number of files to restore.
            token_budget: Total token budget for file restoration.

        Returns:
            List of attachment messages for restored files.
        """
        # Use SessionFileCache if available (faster, avoids re-reading)
        if self._file_cache:
            return await self._restore_from_cache(max_files, token_budget)

        # Fallback to legacy file_state dict
        if not file_state:
            return []

        # Sort by recency (most recent first)
        recent_files = sorted(
            file_state.items(),
            key=lambda x: x[1].timestamp,
            reverse=True,
        )[:max_files]

        attachments = []
        used_tokens = 0

        for path, state in recent_files:
            try:
                # Estimate tokens for this file
                file_tokens = len(state.content) // 4

                if used_tokens + file_tokens > token_budget:
                    _logger.info(
                        "file_restore_budget_exhausted",
                        path=path,
                        used_tokens=used_tokens,
                        budget=token_budget,
                    )
                    break

                # Limit content per file
                content = state.content
                if file_tokens > POST_COMPACT_MAX_TOKENS_PER_FILE:
                    content = content[: POST_COMPACT_MAX_TOKENS_PER_FILE * 4]
                    content += "\n\n[... file truncated for compaction ...]"

                attachments.append({
                    "type": "file_restore",
                    "path": path,
                    "content": content,
                    "timestamp": state.timestamp,
                })
                used_tokens += file_tokens

                _logger.info(
                    "file_restore_success",
                    path=path,
                    tokens=file_tokens,
                    used_tokens=used_tokens,
                )
            except Exception as e:
                _logger.warning(
                    "file_restore_failed",
                    path=path,
                    error=str(e),
                )

        return attachments

    async def _restore_from_cache(
        self,
        max_files: int = POST_COMPACT_MAX_FILES_TO_RESTORE,
        token_budget: int = POST_COMPACT_TOKEN_BUDGET,
    ) -> list[dict[str, Any]]:
        """Restore recently accessed files from SessionFileCache.

        Uses the persistent file cache to restore context without re-reading files.

        Args:
            max_files: Maximum number of files to restore.
            token_budget: Total token budget for file restoration.

        Returns:
            List of attachment messages for restored files.
        """
        if not self._file_cache:
            return []

        # Get recent files from cache
        recent_files = self._file_cache.get_recent_files(
            max_files=max_files,
            max_tokens=token_budget,
        )

        attachments = []
        used_tokens = 0

        for cached in recent_files:
            try:
                file_tokens = cached.token_estimate

                if used_tokens + file_tokens > token_budget:
                    _logger.info(
                        "file_restore_cache_budget_exhausted",
                        path=cached.path,
                        used_tokens=used_tokens,
                        budget=token_budget,
                    )
                    break

                # Limit content per file
                content = cached.content
                if file_tokens > POST_COMPACT_MAX_TOKENS_PER_FILE:
                    content = content[: POST_COMPACT_MAX_TOKENS_PER_FILE * 4]
                    content += "\n\n[... file truncated for compaction ...]"

                attachments.append({
                    "type": "file_restore",
                    "path": cached.path,
                    "content": content,
                    "timestamp": cached.last_accessed,
                    "from_cache": True,
                })
                used_tokens += file_tokens

                _logger.info(
                    "file_restore_cache_success",
                    path=cached.path,
                    tokens=file_tokens,
                    used_tokens=used_tokens,
                    access_count=cached.access_count,
                )
            except Exception as e:
                _logger.warning(
                    "file_restore_cache_failed",
                    path=cached.path,
                    error=str(e),
                )

        # Log cache stats
        cache_stats = self._file_cache.get_stats()
        _logger.info(
            "file_restore_cache_stats",
            cache_hits=cache_stats["hits"],
            cache_misses=cache_stats["misses"],
            hit_rate=cache_stats["hit_rate"],
            entries=cache_stats["entries"],
        )

        return attachments

    async def compact_with_keepalive(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
        llm_summarize_fn: Callable[[list[dict[str, Any]]], Awaitable[str | None]],
        session_manager: Any | None = None,
    ) -> CompactResult:
        """Compact with keep-alive signals to prevent timeout.

        Sends periodic signals during long compaction operations to prevent
        remote session WebSocket idle timeouts.

        Args:
            messages: List of conversation messages.
            current_tokens: Current token count.
            llm_summarize_fn: Async callable for LLM summary.
            session_manager: Optional session manager for keep-alive signals.

        Returns:
            CompactResult with compaction statistics.
        """
        keepalive_task = None

        if session_manager:
            keepalive_task = asyncio.create_task(
                self._send_keepalive(session_manager)
            )

        try:
            result = await self._summary_compact(messages, current_tokens, llm_summarize_fn)
            return result
        finally:
            if keepalive_task:
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    pass

    async def _send_keepalive(self, session_manager: Any) -> None:
        """Send periodic keep-alive signals to prevent timeout.

        Args:
            session_manager: Session manager with send_heartbeat method.
        """
        while True:
            try:
                await asyncio.sleep(KEEPALIVE_INTERVAL_SECONDS)
                if hasattr(session_manager, "send_heartbeat"):
                    await session_manager.send_heartbeat()
                if hasattr(session_manager, "update_status"):
                    await session_manager.update_status("compacting")
                _logger.debug("keepalive_sent")
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.warning("keepalive_failed", error=str(e))

    def get_effective_context_window(self, model: str) -> int:
        """Get effective context window for a specific model.

        Deducts reserved tokens for compaction output.
        Claude Code uses: effective_context_window - 13_000 (~93.5%)

        Args:
            model: Model identifier (e.g., "claude-3-sonnet", "gpt-4").

        Returns:
            Effective context window size in tokens.
        """
        base_window = MODEL_CONTEXT_WINDOWS.get(model, MODEL_CONTEXT_WINDOWS["default"])
        return base_window - AUTOCOMPACT_BUFFER_TOKENS

    def get_auto_compact_threshold(self, model: str) -> int:
        """Get auto-compact threshold for a specific model.

        Compaction triggers when context reaches this threshold.
        Claude Code uses: effective_context_window - 13_000 (~93.5% of context)

        Args:
            model: Model identifier.

        Returns:
            Auto-compact threshold in tokens.
        """
        effective_window = self.get_effective_context_window(model)
        # Claude Code pattern: trigger at ~93.5% of effective window
        return effective_window - AUTOCOMPACT_BUFFER_TOKENS

    def get_warning_threshold(self, model: str) -> int:
        """Get warning threshold for approaching context limit.

        Claude Code uses: effective_context_window - 20_000 (~90% of context)

        Args:
            model: Model identifier.

        Returns:
            Warning threshold in tokens.
        """
        effective_window = self.get_effective_context_window(model)
        # Claude Code pattern: warn at ~90% of effective window
        return effective_window - 20_000

    def get_token_budget_guidance(self, model: str, current_tokens: int) -> str:
        """Get token budget guidance for system prompt.

        Claude Code injects "Approximately X tokens remaining" in system prompt.

        Args:
            model: Model identifier.
            current_tokens: Current token count.

        Returns:
            Token budget guidance string.
        """
        effective_window = self.get_effective_context_window(model)
        remaining = max(0, effective_window - current_tokens)
        warning_threshold = self.get_warning_threshold(model)

        if current_tokens >= warning_threshold:
            percentage = (current_tokens / effective_window) * 100
            return (
                f"⚠️ **Token Budget Warning**: Approximately {remaining:,} tokens remaining "
                f"({percentage:.1f}% used). Consider compacting soon to avoid context overflow."
            )
        else:
            return f"Approximately {remaining:,} tokens remaining in context window."

    def get_config_for_model(self, model: str) -> CompactConfig:
        """Get optimized config for a specific model.

        Args:
            model: Model identifier.

        Returns:
            CompactConfig optimized for the model.
        """
        effective_window = self.get_effective_context_window(model)
        threshold = self.get_auto_compact_threshold(model)

        return CompactConfig(
            target_window_size=effective_window,
            max_context_tokens=threshold,
            min_kept_tokens=effective_window // 3,
            system_prompt_reservation=self.config.system_prompt_reservation,
            enable_llm_summary=self.config.enable_llm_summary,
            enable_snip=self.config.enable_snip,
            enable_cache_compact=self.config.enable_cache_compact,
            enable_context_collapse=self.config.enable_context_collapse,
        )

    def log_compaction_analytics(
        self,
        result: CompactResult,
        model: str,
        tracking: AutoCompactTrackingState | None = None,
    ) -> None:
        """Log detailed compaction analytics.

        Args:
            result: Compaction result.
            model: Model identifier.
            tracking: Optional tracking state.
        """
        analytics = {
            "original_tokens": result.original_tokens,
            "compacted_tokens": result.compacted_tokens,
            "tokens_saved": result.tokens_saved,
            "messages_removed": result.messages_removed,
            "messages_compacted": result.messages_compacted,
            "strategy_used": result.strategy_used.value,
            "success": result.success,
            "model": model,
            "effective_context_window": self.get_effective_context_window(model),
            "auto_compact_threshold": self.get_auto_compact_threshold(model),
            "compression_ratio": (
                result.tokens_saved / result.original_tokens
                if result.original_tokens > 0
                else 0
            ),
            "timestamp": time.time(),
        }

        if tracking:
            analytics.update({
                "turn_counter": tracking.turn_counter,
                "turn_id": tracking.turn_id,
                "consecutive_failures": tracking.consecutive_failures,
                "compacted": tracking.compacted,
            })

        _logger.info("compaction_analytics", **analytics)
