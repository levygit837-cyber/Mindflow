"""Personality management interfaces.

Defines contracts for personality selection, rule evaluation,
and personality-based task configuration.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mindflow_backend.schemas.orchestration.personality import SpecialistDecisionResult


@runtime_checkable
class SpecialistSelector(Protocol):
    """Contract for personality selection implementations."""
    
    def select_specialist(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        context_requirements: list[str] | None = None,
        current_specialist: str | None = None,
    ) -> SpecialistDecisionResult:
        """Select optimal personality for a task."""
        ...

    def create_switch_context(
        self,
        from_specialist: str,
        to_specialist: str,
        task_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Create context for personality switch."""
        ...

    def evaluate_personality_fit(
        self,
        task_requirements: dict[str, Any],
        personality_traits: dict[str, Any],
    ) -> float:
        """Evaluate personality fit for task requirements."""
        ...


@runtime_checkable
class RuleEngine(Protocol):
    """Contract for personality rule evaluation."""
    
    def evaluate_switch_rules(
        self,
        current_context: dict[str, Any],
        trigger_conditions: dict[str, Any],
    ) -> bool:
        """Evaluate personality switch trigger conditions."""
        ...
    
    def get_active_rules(
        self,
        personality_id: str,
    ) -> list[dict[str, Any]]:
        """Get active rules for personality."""
        ...
    
    def update_rules(
        self,
        personality_id: str,
        rules: list[dict[str, Any]],
    ) -> bool:
        """Update personality rules."""
        ...
