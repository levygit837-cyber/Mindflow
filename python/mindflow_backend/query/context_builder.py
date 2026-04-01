"""Context Builder for QueryEngine.

Builds context from multiple providers:
- Git: repository state, branch, commits
- File: file contents, structure
- Memory: session memory, project memory
- MCP: MCP server context

Inspired by Claude Code's context management system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ContextProviderType(str, Enum):
    """Types of context providers."""

    GIT = "git"
    FILE = "file"
    MEMORY = "memory"
    MCP = "mcp"
    CUSTOM = "custom"


@dataclass
class ContextProviderConfig:
    """Configuration for a context provider."""

    name: str
    provider_type: ContextProviderType
    priority: int = 0
    max_tokens: int = 10_000
    enabled: bool = True


@dataclass
class ContextResult:
    """Result of context building."""

    context: str
    tokens: int
    providers_used: list[str]
    total_providers: int
    truncated: bool = False


class ContextProvider:
    """Base class for context providers."""

    def __init__(self, config: ContextProviderConfig) -> None:
        self.config = config

    async def get_context(self, query: str) -> str | None:
        """Get context from this provider.

        Args:
            query: The query to get context for.

        Returns:
            Context string or None if unavailable.
        """
        raise NotImplementedError


class ContextBuilder:
    """Builds context from multiple providers for QueryEngine.

    Inspired by Claude Code's context management system.
    Handles:
    - Multiple context providers (Git, File, Memory, MCP)
    - Token budget management
    - Priority-based provider ordering
    - Context truncation
    """

    def __init__(self, providers: list[ContextProvider] | None = None) -> None:
        """Initialize context builder with providers."""
        self.providers = providers or []

    def add_provider(self, provider: ContextProvider) -> None:
        """Add a context provider.

        Args:
            provider: The context provider to add.
        """
        self.providers.append(provider)

    async def build_context(
        self,
        query: str,
        max_tokens: int = 100_000,
    ) -> ContextResult:
        """Build context from all providers.

        Args:
            query: The query to build context for.
            max_tokens: Maximum tokens for context.

        Returns:
            ContextResult with context data.
        """
        # Sort providers by priority (higher priority first)
        sorted_providers = sorted(
            [p for p in self.providers if p.config.enabled],
            key=lambda p: p.config.priority,
            reverse=True,
        )

        context_parts = []
        providers_used = []
        total_tokens = 0

        for provider in sorted_providers:
            if total_tokens >= max_tokens:
                break

            try:
                provider_context = await provider.get_context(query)
                if provider_context:
                    # Truncate if provider has max_tokens limit
                    if provider.config.max_tokens:
                        provider_context = self._truncate_to_tokens(
                            provider_context,
                            provider.config.max_tokens,
                        )

                    context_parts.append(provider_context)
                    providers_used.append(provider.config.name)
                    total_tokens += len(provider_context) // 4

                    _logger.debug(
                        "context_provider_used",
                        provider=provider.config.name,
                        tokens=len(provider_context) // 4,
                        total_tokens=total_tokens,
                    )
            except Exception as e:
                _logger.warning(
                    "context_provider_failed",
                    provider=provider.config.name,
                    error=str(e),
                )
                continue

        context_str = "\n\n".join(context_parts)

        return ContextResult(
            context=context_str,
            tokens=total_tokens,
            providers_used=providers_used,
            total_providers=len(sorted_providers),
            truncated=total_tokens >= max_tokens,
        )

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximate token count.

        Args:
            text: Text to truncate.
            max_tokens: Maximum tokens.

        Returns:
            Truncated text.
        """
        max_chars = max_tokens * 4  # ~4 chars per token
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n[... truncated ...]"
