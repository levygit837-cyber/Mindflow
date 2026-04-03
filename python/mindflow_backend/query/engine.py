"""QueryEngine — orchestrates query lifecycle with budget management.

Mirrors Claude Code's QueryEngine architecture:
- Manages context building from multiple providers
- Enforces token budget during query execution
- Handles query lifecycle (start, execute, complete)
- Integrates with permission system for tool calls
- Integrates with SessionFileCache for file caching
- Integrates with AutoCompactService for context compaction

Usage:
    engine = QueryEngine(
        providers=[GitProvider(), FileProvider(), MemoryProvider()],
        budget=TokenBudget(max_tokens=200_000),
        permission_manager=permission_manager,
    )
    context = await engine.build_context(query="How does auth work?")
    result = await engine.execute(context)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from mindflow_backend.permissions.types import PermissionContext, PermissionMode
from mindflow_backend.query.budget.auto_compact import AutoCompactService
from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.cache.file_cache import SessionFileCache, create_session_cache

if TYPE_CHECKING:
    from mindflow_backend.permissions.manager import PermissionManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context Provider Protocol
# ---------------------------------------------------------------------------


class ContextProvider(Protocol):
    """Protocol for context data providers.

    Each provider fetches contextual data from a different source:
    - GitProvider: git status, diffs, branch info
    - FileProvider: file contents, directory listings
    - MemoryProvider: session/project memory retrieval
    - MCPProvider: MCP server resources and tools

    Providers return (source_label, content, priority) tuples.
    """

    @property
    def name(self) -> str:
        """Provider name for logging."""
        ...

    async def fetch(self, query: str, budget: TokenBudget) -> str | None:
        """Fetch context data.

        Args:
            query: The user's query (for relevant context)
            budget: Token budget to respect (check remaining before fetching)

        Returns:
            Context text or None if nothing to contribute
        """
        ...

    @property
    def priority(self) -> int:
        """Priority for ordering and trimming (higher = more important)."""
        return 50


# ---------------------------------------------------------------------------
# Query Context
# ---------------------------------------------------------------------------


@dataclass
class QueryContext:
    """Assembled context for a query execution."""

    query: str
    system_prompt: str
    assembled_context: str
    budget: TokenBudget
    permission_context: PermissionContext
    metadata: dict[str, int] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.budget.total_tokens


# ---------------------------------------------------------------------------
# Query Engine
# ---------------------------------------------------------------------------


class QueryEngine:
    """Main query orchestration engine.

    Responsible for:
    1. Building context from providers within budget
    2. Assembling system prompt + context
    3. Executing queries (delegated to LLM client)
    4. Tracking token usage across the conversation
    5. Caching files via SessionFileCache
    6. Auto-compacting context when near limits

    This mirrors Claude Code's QueryEngine but is adapted for MindFlow's
    multi-agent architecture where each agent may have its own QueryEngine.
    """

    def __init__(
        self,
        providers: list[ContextProvider],
        budget: TokenBudget | None = None,
        system_prompt: str = "",
        permission_manager: PermissionManager | None = None,
        session_id: str | None = None,
        use_file_cache: bool = True,
    ) -> None:
        self._providers = sorted(providers, key=lambda p: -p.priority)
        self._budget = budget or TokenBudget()
        self._system_prompt = system_prompt
        self._permission_manager = permission_manager

        # File cache for avoiding re-reads
        self._file_cache: SessionFileCache | None = None
        if use_file_cache and session_id:
            self._file_cache = create_session_cache(session_id)
            logger.info(
                "query_engine_file_cache_enabled",
                session_id=session_id,
            )

        # Auto-compact service for context management
        self._auto_compact = AutoCompactService(
            file_cache=self._file_cache,
            session_id=session_id,
        )

    @property
    def budget(self) -> TokenBudget:
        return self._budget

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def file_cache(self) -> SessionFileCache | None:
        """Get the file cache instance."""
        return self._file_cache

    @property
    def auto_compact(self) -> AutoCompactService:
        """Get the auto-compact service instance."""
        return self._auto_compact

    async def read_file_with_cache(
        self,
        file_path: str,
        encoding: str = "utf-8",
    ) -> str | None:
        """Read a file using the session cache.

        Uses SessionFileCache to avoid re-reading unchanged files.

        Args:
            file_path: Path to the file.
            encoding: File encoding (default: utf-8).

        Returns:
            File content as string, or None if file doesn't exist.
        """
        if self._file_cache:
            return await self._file_cache.get_or_read(file_path, encoding)

        # Fallback: read directly without cache
        try:
            with open(file_path, encoding=encoding) as f:
                return f.read()
        except (FileNotFoundError, PermissionError):
            return None

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats: dict[str, Any] = {
            "file_cache_enabled": self._file_cache is not None,
            "auto_compact_enabled": True,
        }

        if self._file_cache:
            stats["file_cache"] = self._file_cache.get_stats()

        return stats

    async def build_context(
        self,
        query: str,
        permission_context: PermissionContext | None = None,
    ) -> QueryContext:
        """Build query context from all providers within budget.

        Executes providers in priority order (highest first).
        Each provider receives the current budget state so it can
        limit its output accordingly.

        Args:
            query: The user's query
            permission_context: Current permission state

        Returns:
            QueryContext with assembled context and budget state
        """
        self._budget.reset()

        # Add system prompt first (highest priority)
        if self._system_prompt:
            self._budget.add_context(
                source="system_prompt",
                content=self._system_prompt,
                priority=100,
            )

        # Fetch from each provider within budget
        metadata: dict[str, int] = {}
        for provider in self._providers:
            if self._budget.is_near_limit():
                logger.warning(
                    f"Skipping provider '{provider.name}' — near budget limit "
                    f"({self._budget.utilization:.0%})"
                )
                break

            try:
                content = await provider.fetch(query, self._budget)
                if content:
                    tokens = self._budget.add_context(
                        source=f"provider:{provider.name}",
                        content=content,
                        priority=provider.priority,
                    )
                    metadata[f"tokens_{provider.name}"] = tokens
                    logger.debug(
                        f"Provider '{provider.name}' contributed {tokens} tokens"
                    )
            except Exception:
                logger.exception(f"Provider '{provider.name}' failed")

        # Trim if over budget
        if self._budget.is_over_budget():
            trimmed = self._budget.trim_to_fit()
            for ctx in trimmed:
                logger.warning(
                    f"Trimmed context section from '{ctx.source}' "
                    f"({ctx.token_count} tokens, priority={ctx.priority})"
                )

        assembled = self._budget.assemble()

        return QueryContext(
            query=query,
            system_prompt=self._system_prompt,
            assembled_context=assembled,
            budget=self._budget,
            permission_context=permission_context or PermissionContext(
                mode=PermissionMode.DEFAULT,
            ),
            metadata=metadata,
        )

    async def fetch_provider_summary(
        self, provider_name: str, query: str
    ) -> str | None:
        """Fetch context from a single provider (for debugging/inspection)."""
        for provider in self._providers:
            if provider.name == provider_name:
                return await provider.fetch(query, self._budget)
        raise ValueError(f"Provider '{provider_name}' not found")

    def add_provider(self, provider: ContextProvider) -> None:
        """Add a context provider at runtime."""
        self._providers.append(provider)
        self._providers.sort(key=lambda p: -p.priority)
        logger.info(f"Added provider: '{provider.name}' (priority={provider.priority})")

    def remove_provider(self, provider_name: str) -> bool:
        """Remove a context provider by name."""
        before = len(self._providers)
        self._providers = [
            p for p in self._providers if p.name != provider_name
        ]
        removed = len(self._providers) < before
        if removed:
            logger.info(f"Removed provider: '{provider_name}'")
        return removed

    def get_budget_summary(self) -> dict[str, Any]:
        """Get current budget utilization summary."""
        summary = self._budget.summary()
        summary["by_provider"] = self._budget.get_usage_by_source()
        return summary

    def reset(self) -> None:
        """Reset engine state for a new conversation."""
        self._budget.reset()
        logger.info("QueryEngine reset")
