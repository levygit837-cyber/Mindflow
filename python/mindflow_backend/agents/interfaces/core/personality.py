"""Personality management interfaces.

Defines contracts for personality selection, rule evaluation,
and personality-based task configuration.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mindflow_backend.schemas.orchestration.personality import PersonalityDecisionResult


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
