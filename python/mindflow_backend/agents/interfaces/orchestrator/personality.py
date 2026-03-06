"""Personality manager interface.

Defines the contract for dynamic personality selection, switching,
and configuration based on personality.py schemas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from mindflow_backend.schemas.orchestration.personality import (
    PersonalityConfiguration,
    PersonalityDecisionResult,
    PersonalitySelection,
    PersonalitySelectionRule,
    PersonalitySwitchContext,
    PersonalityType,
)


@runtime_checkable
class PersonalityManagerContract(Protocol):
    """Contract for personality management and dynamic selection.
    
    Handles personality selection decisions, switching operations,
    rule evaluation, and configuration management.
    """

    async def select_personality(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        context_requirements: list[str] | None = None,
        current_personality: PersonalityType | None = None,
    ) -> PersonalityDecisionResult:
        """Select optimal personality for a given task.
        
        Args:
            task_id: Unique task identifier.
            task_description: Description of the task.
            task_complexity: Complexity level (simple/medium/complex).
            context_requirements: Required context capabilities.
            current_personality: Currently active personality.
            
        Returns:
            Complete personality selection decision with configuration.
        """
        ...

    async def switch_personality(
        self,
        session_id: str,
        from_personality: PersonalityType,
        to_personality: PersonalityType,
        trigger: str,
        rationale: str,
        carry_over_context: str = "",
    ) -> PersonalitySwitchContext:
        """Execute a personality switch operation.
        
        Args:
            session_id: Session identifier.
            from_personality: Current personality.
            to_personality: Target personality.
            trigger: What triggered the switch.
            rationale: Reason for switching.
            carry_over_context: Context to preserve.
            
        Returns:
            Context for the personality switch operation.
        """
        ...

    async def configure_personality(
        self,
        personality: PersonalityType,
        configuration: PersonalityConfiguration,
    ) -> None:
        """Configure a specific personality.
        
        Args:
            personality: Personality type to configure.
            configuration: Personality configuration parameters.
        """
        ...

    async def get_personality_configuration(
        self,
        personality: PersonalityType,
    ) -> PersonalityConfiguration:
        """Get current configuration for a personality.
        
        Args:
            personality: Personality type.
            
        Returns:
            Current personality configuration.
        """
        ...

    async def evaluate_selection_rules(
        self,
        task_description: str,
        task_complexity: str,
        specialization: str | None = None,
    ) -> list[PersonalitySelectionRule]:
        """Evaluate personality selection rules.
        
        Args:
            task_description: Task description.
            task_complexity: Complexity level.
            specialization: Required specialization.
            
        Returns:
            List of applicable selection rules ranked by priority.
        """
        ...

    async def add_selection_rule(
        self,
        rule: PersonalitySelectionRule,
    ) -> None:
        """Add a new personality selection rule.
        
        Args:
            rule: Selection rule to add.
        """
        ...

    async def remove_selection_rule(
        self,
        rule_name: str,
    ) -> bool:
        """Remove a personality selection rule.
        
        Args:
            rule_name: Name of rule to remove.
            
        Returns:
            True if rule was removed.
        """
        ...

    async def get_personality_performance(
        self,
        personality: PersonalityType,
        time_window: str = "24h",
    ) -> dict[str, float]:
        """Get performance metrics for a personality.
        
        Args:
            personality: Personality type.
            time_window: Time window for metrics.
            
        Returns:
            Performance metrics dictionary.
        """
        ...

    async def should_switch_personality(
        self,
        current_task: dict,
        current_personality: PersonalityType,
        performance_metrics: dict[str, float],
    ) -> bool:
        """Determine if personality should be switched.
        
        Args:
            current_task: Current task context.
            current_personality: Active personality.
            performance_metrics: Current performance metrics.
            
        Returns:
            True if personality switch is recommended.
        """
        ...

    async def create_switch_context(
        self,
        session_id: str,
        from_personality: PersonalityType,
        to_personality: PersonalityType,
        trigger: str,
        rationale: str,
        carry_over_context: str = "",
    ) -> dict[str, any]:
        """Create context for personality switching.
        
        Args:
            session_id: Session identifier.
            from_personality: Source personality.
            to_personality: Target personality.
            trigger: Switch trigger.
            rationale: Switch rationale.
            carry_over_context: Context to preserve.
            
        Returns:
            Context dictionary for personality switch.
        """
        ...

    async def optimize_personality_selection(
        self,
        task_history: list[dict],
        performance_data: dict[str, dict],
    ) -> list[PersonalitySelectionRule]:
        """Optimize personality selection rules based on performance.
        
        Args:
            task_history: Historical task data.
            performance_data: Performance metrics by personality.
            
        Returns:
            Optimized selection rules.
        """
        ...

    async def get_available_personalities(self) -> list[PersonalityType]:
        """Get list of available personality types.
        
        Returns:
            List of configured personality types.
        """
        ...

    async def validate_personality_configuration(
        self,
        configuration: PersonalityConfiguration,
    ) -> bool:
        """Validate personality configuration.
        
        Args:
            configuration: Configuration to validate.
            
        Returns:
            True if configuration is valid.
        """
        ...
