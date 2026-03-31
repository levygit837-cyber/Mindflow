"""Base class for context providers."""

from abc import ABC, abstractmethod


class BaseContextProvider(ABC):
    """Base class for context providers.

    Attributes:
        name: Provider name (e.g., "git", "file", "memory")
        priority: Priority for ordering (higher = fetched first, kept longer)
    """

    priority: int = 50  # Default medium priority

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and source tracking."""

    @abstractmethod
    async def fetch(self, query: str, max_tokens: int = 0) -> str | None:
        """Fetch context data.

        Args:
            query: The user's query (for relevant context)
            max_tokens: Token budget limit for this provider (0 = no limit)

        Returns:
            Context text or None if nothing to contribute.
        """