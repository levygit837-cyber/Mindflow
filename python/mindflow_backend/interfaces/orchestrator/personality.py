"""Personality manager interface.

Defines the contract for dynamic personality selection, switching,
and configuration based on personality.py schemas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from mindflow_backend.schemas.orchestration.personality import (
    SpecialistConfiguration,
    SpecialistDecisionResult,
    SpecialistSelection,
    SpecialistSelectionRule,
    SpecialistSwitchContext,
    SpecialistType,
)


@runtime_checkable
class PersonalityManagerContract(Protocol):
    """Contract for personality management and dynamic selection.
    
    Handles personality selection decisions, switching operations,
    rule evaluation, and configuration management.
    """

    async def select_specialist(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        context_requirements: list[str] | None = None,
        current_specialist: str | None = None,
    ) -> SpecialistDecisionResult:
        """Select optimal specialist for task execution."""
        ...

    async def switch_personality(
        self,
        task_id: str,
        from_specialist: SpecialistType,
        to_specialist: SpecialistType,
        context: SpecialistSwitchContext,
    ) -> bool:
        """Execute personality switch during task execution."""
        ...

    async def evaluate_personality_rules(
        self,
        task_context: dict[str, Any],
        rules: list[SpecialistSelectionRule],
    ) -> list[SpecialistSelection]:
        """Evaluate personality selection rules."""
        ...

    async def get_specialist_config(
        self,
        specialist_type: SpecialistType,
    ) -> SpecialistConfiguration:
        """Get configuration for specialist type."""
        ...

    async def update_specialist_config(
        self,
        specialist_type: SpecialistType,
        config: SpecialistConfiguration,
    ) -> bool:
        """Update specialist configuration."""
        ...
