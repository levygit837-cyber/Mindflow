"""System Context Cache — reduces API cost with prompt caching.

Inspired by Claude Code's static/dynamic prompt split:
- Caches static parts of system prompt (tools, base instructions)
- Only sends dynamic parts on each turn (memory, git, session-specific)
- Uses Anthropic's cache_control for prompt caching

Usage:
    cache = SystemContextCache()
    cache.set_static_prefix(static_content)
    messages = cache.build_messages(dynamic_content)
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Default cache TTL (5 minutes)
DEFAULT_CACHE_TTL = 300

# Minimum content length for caching (100 tokens)
MIN_CACHE_TOKENS = 100


@dataclass
class CachedContext:
    """A cached context entry."""

    content: str
    content_hash: str
    token_estimate: int
    cached_at: float = field(default_factory=time.time)
    cache_hits: int = 0
    last_used: float = field(default_factory=time.time)

    def is_valid(self, ttl: int = DEFAULT_CACHE_TTL) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - self.cached_at) < ttl

    def touch(self) -> None:
        """Update access statistics."""
        self.cache_hits += 1
        self.last_used = time.time()


class SystemContextCache:
    """Cache for system context to reduce API costs.

    Features:
    - Static/dynamic prompt split
    - Content hash-based invalidation
    - Token estimation for budget management
    - Cache statistics tracking

    Usage:
        cache = SystemContextCache()
        
        # Set static prefix (tools, base instructions)
        cache.set_static_prefix(tools_content)
        
        # Build messages with cached static + dynamic
        messages = cache.build_messages(dynamic_content)
        
        # Use with Anthropic API
        response = client.messages.create(
            messages=messages,
            cache_control={"type": "ephemeral"}
        )
    """

    def __init__(
        self,
        ttl: int = DEFAULT_CACHE_TTL,
        min_cache_tokens: int = MIN_CACHE_TOKENS,
    ) -> None:
        self.ttl = ttl
        self.min_cache_tokens = min_cache_tokens

        # Cached contexts
        self._static_prefix: CachedContext | None = None
        self._dynamic_cache: dict[str, CachedContext] = {}

        # Statistics
        self._stats = {
            "static_hits": 0,
            "static_misses": 0,
            "dynamic_hits": 0,
            "dynamic_misses": 0,
            "tokens_saved": 0,
        }

    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count (rough: 1 token ≈ 4 chars)."""
        return len(content) // 4

    def _compute_hash(self, content: str) -> str:
        """Compute content hash for change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def set_static_prefix(self, content: str) -> None:
        """Set the static prefix for caching.

        This content will be cached and reused across turns.

        Args:
            content: Static content (tools, base instructions, etc.)
        """
        token_estimate = self._estimate_tokens(content)

        if token_estimate < self.min_cache_tokens:
            logger.debug(
                "system_context_cache_skip_small",
                tokens=token_estimate,
                min_required=self.min_cache_tokens,
            )
            return

        self._static_prefix = CachedContext(
            content=content,
            content_hash=self._compute_hash(content),
            token_estimate=token_estimate,
        )

        logger.info(
            "system_context_cache_static_set",
            tokens=token_estimate,
            hash=self._static_prefix.content_hash,
        )

    def get_static_prefix(self) -> str | None:
        """Get the cached static prefix.

        Returns:
            Static content if valid, None otherwise.
        """
        if not self._static_prefix:
            self._stats["static_misses"] += 1
            return None

        if not self._static_prefix.is_valid(self.ttl):
            self._stats["static_misses"] += 1
            return None

        self._static_prefix.touch()
        self._stats["static_hits"] += 1
        self._stats["tokens_saved"] += self._static_prefix.token_estimate

        return self._static_prefix.content

    def set_dynamic_context(self, key: str, content: str) -> None:
        """Set a dynamic context entry.

        Dynamic contexts are session-specific and change between turns.

        Args:
            key: Context key (e.g., "git_status", "memory", "environment")
            content: Dynamic content
        """
        token_estimate = self._estimate_tokens(content)

        self._dynamic_cache[key] = CachedContext(
            content=content,
            content_hash=self._compute_hash(content),
            token_estimate=token_estimate,
        )

        logger.debug(
            "system_context_cache_dynamic_set",
            key=key,
            tokens=token_estimate,
        )

    def get_dynamic_context(self, key: str) -> str | None:
        """Get a dynamic context entry.

        Args:
            key: Context key

        Returns:
            Dynamic content if valid, None otherwise.
        """
        cached = self._dynamic_cache.get(key)

        if not cached:
            self._stats["dynamic_misses"] += 1
            return None

        if not cached.is_valid(self.ttl):
            del self._dynamic_cache[key]
            self._stats["dynamic_misses"] += 1
            return None

        cached.touch()
        self._stats["dynamic_hits"] += 1
        self._stats["tokens_saved"] += cached.token_estimate

        return cached.content

    def build_messages(
        self,
        dynamic_content: str,
        include_cache_control: bool = True,
    ) -> list[dict[str, Any]]:
        """Build messages with cached static prefix + dynamic content.

        Args:
            dynamic_content: Dynamic content for this turn
            include_cache_control: Whether to include cache_control for Anthropic API

        Returns:
            List of messages ready for API call
        """
        messages = []

        # Add static prefix with cache control
        static_content = self.get_static_prefix()
        if static_content:
            static_msg: dict[str, Any] = {
                "role": "system",
                "content": static_content,
            }
            if include_cache_control:
                static_msg["cache_control"] = {"type": "ephemeral"}
            messages.append(static_msg)

        # Add dynamic content
        if dynamic_content:
            messages.append({
                "role": "system",
                "content": dynamic_content,
            })

        return messages

    def build_system_prompt(
        self,
        static_parts: list[str],
        dynamic_parts: list[str],
    ) -> str:
        """Build a system prompt from static and dynamic parts.

        Args:
            static_parts: Static content parts (cached)
            dynamic_parts: Dynamic content parts (not cached)

        Returns:
            Combined system prompt
        """
        parts = []

        # Add static parts
        for part in static_parts:
            if part:
                parts.append(part)

        # Add dynamic parts
        for part in dynamic_parts:
            if part:
                parts.append(part)

        return "\n\n".join(parts)

    def clear(self) -> None:
        """Clear all cached contexts."""
        self._static_prefix = None
        self._dynamic_cache.clear()
        logger.info("system_context_cache_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_hits = self._stats["static_hits"] + self._stats["dynamic_hits"]
        total_misses = self._stats["static_misses"] + self._stats["dynamic_misses"]
        total = total_hits + total_misses

        hit_rate = total_hits / total if total > 0 else 0

        return {
            "static_prefix_set": self._static_prefix is not None,
            "static_tokens": (
                self._static_prefix.token_estimate if self._static_prefix else 0
            ),
            "dynamic_entries": len(self._dynamic_cache),
            "static_hits": self._stats["static_hits"],
            "static_misses": self._stats["static_misses"],
            "dynamic_hits": self._stats["dynamic_hits"],
            "dynamic_misses": self._stats["dynamic_misses"],
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_rate": round(hit_rate, 3),
            "tokens_saved": self._stats["tokens_saved"],
        }


def create_system_context_cache(
    ttl: int = DEFAULT_CACHE_TTL,
    **kwargs: Any,
) -> SystemContextCache:
    """Create a system context cache.

    Args:
        ttl: Cache TTL in seconds
        **kwargs: Additional arguments for SystemContextCache

    Returns:
        SystemContextCache instance
    """
    return SystemContextCache(ttl=ttl, **kwargs)