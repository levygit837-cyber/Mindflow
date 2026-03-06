"""Core interfaces for agent system.

Defines contracts that all agent system components must implement
to ensure loose coupling and testability.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any
from mindflow_backend.schemas.session.contracts import RetrievedContext
from mindflow_backend.schemas.session.review import ReviewExecutionContext
from mindflow_backend.schemas.orchestration.personality import PersonalityDecisionResult


@runtime_checkable
class ContextRetriever(Protocol):
    """Contract for context retrieval implementations."""
    
    async def get_relevant_context(
        self,
        agent_id: str,
        query: str,
        session_id: str,
        context_window: tuple[int, int] = (0, 100000),
        include_related: bool = True,
        max_results: int = 5,
    ) -> RetrievedContext:
        """Retrieve relevant context for an agent."""
        ...

    async def get_context_window(
        self,
        session_id: str,
        token_range: tuple[int, int],
        include_related: bool = False,
    ) -> RetrievedContext:
        """Get context from specific token window."""
        ...

    async def get_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[RetrievedContext]:
        """Get context using semantic search."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Contract for vector storage implementations."""
    
    async def search_session_context(
        self,
        session_id: str,
        query_vector: list[float],
        limit: int,
        score_threshold: float,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors in session context."""
        ...

    async def create_session_collection(self, session_id: str) -> None:
        """Create collection for session vectors."""
        ...

    async def store_vectors(
        self,
        session_id: str,
        vectors: list[dict[str, Any]],
    ) -> None:
        """Store vectors with metadata."""
        ...
    
    async def search_subtask_context(
        self,
        session_id: str,
        task_id: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        include_dependencies: bool = True,
    ) -> list[dict[str, Any]]:
        """Search for context relevant to specific sub-task."""
        ...
    
    async def store_subtask_context(
        self,
        session_id: str,
        task_id: str,
        agent_type: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> str:
        """Store context for a specific sub-task with dependencies."""
        ...
    
    async def get_task_dependencies_context(
        self,
        session_id: str,
        task_id: str,
        dependency_task_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Get context from specific dependency tasks."""
        ...
    
    async def update_task_status(
        self,
        session_id: str,
        task_id: str,
        status: str,
        completion_data: dict[str, Any] | None = None,
    ) -> None:
        """Update the status of a task in the vector store."""
        ...
    
    async def wait_for_task_context(
        self,
        session_id: str,
        task_id: str,
        required_task_ids: list[str],
        timeout_seconds: int = 30,
        poll_interval: float = 0.5,
    ) -> dict[str, Any]:
        """Wait for required task contexts to become available."""
        ...


@runtime_checkable
class PersonalitySelector(Protocol):
    """Contract for personality selection implementations."""
    
    def select_personality(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        context_requirements: list[str] | None = None,
        current_personality: str | None = None,
    ) -> PersonalityDecisionResult:
        """Select optimal personality for a task."""
        ...

    def create_switch_context(
        self,
        session_id: str,
        from_personality: str,
        to_personality: str,
        trigger: str,
        rationale: str,
        carry_over_context: str = "",
    ) -> dict[str, Any]:
        """Create context for personality switching."""
        ...


@runtime_checkable
class ContentAnalyzer(Protocol):
    """Contract for content analysis implementations."""
    
    async def analyze_window(
        self,
        context: ReviewExecutionContext,
    ) -> str:
        """Analyze session window and extract insights."""
        ...


@runtime_checkable
class ResultParser(Protocol):
    """Contract for result parsing implementations."""
    
    def parse_actions(
        self,
        analysis_content: str,
        session_id: str,
        window_range: tuple[int, int],
    ) -> list[dict[str, Any]]:
        """Parse actions from analysis content."""
        ...

    def parse_insights(
        self,
        analysis_content: str,
        session_id: str,
        window_range: tuple[int, int],
    ) -> list[dict[str, Any]]:
        """Parse insights from analysis content."""
        ...


@runtime_checkable
class Cache(Protocol):
    """Generic cache contract."""
    
    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        ...

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        ...

    def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...

    def clear(self) -> None:
        """Clear all cache entries."""
        ...


@runtime_checkable
class RuleEngine(Protocol):
    """Contract for rule evaluation implementations."""
    
    def evaluate(
        self,
        task_description: str,
        task_complexity: str,
        specialization: str | None,
    ) -> list[dict[str, Any]]:
        """Evaluate rules and return candidates."""
        ...

    def add_rule(self, rule: dict[str, Any]) -> None:
        """Add new rule to engine."""
        ...


@runtime_checkable
class Logger(Protocol):
    """Contract for logging implementations."""
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        ...

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        ...

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        ...

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        ...
