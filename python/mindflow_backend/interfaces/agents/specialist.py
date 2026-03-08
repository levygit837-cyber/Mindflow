"""Specialist management interfaces for MindFlow agents.

Defines contracts for specialist selection, rule evaluation,
and specialist-based task configuration.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mindflow_backend.schemas.orchestration.specialists import SpecialistDecisionResult


@runtime_checkable
class SpecialistSelector(Protocol):
    """Contract for specialist selection implementations."""
    
    def select_specialist(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        context_requirements: list[str] | None = None,
        current_specialist: str | None = None,
    ) -> SpecialistDecisionResult:
        """Select optimal specialist for a task."""
        ...

    def create_switch_context(
        self,
        session_id: str,
        from_specialist: str,
        to_specialist: str,
        trigger: str,
        rationale: str,
        carry_over_context: str = "",
    ) -> dict[str, Any]:
        """Create context for specialist switching."""
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
class SpecialistCache(Protocol):
    """Contract for specialist caching implementations."""
    
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
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        ...
