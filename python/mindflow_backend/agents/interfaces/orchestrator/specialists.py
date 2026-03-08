"""Specialist manager interface.

Defines the contract for dynamic specialist selection, switching,
and configuration based on specialists.py schemas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from mindflow_backend.schemas.orchestration.specialists import (
    SpecialistConfiguration,
    SpecialistDecisionResult,
    SpecialistSelection,
    SpecialistSelectionRule,
    SpecialistSwitchContext,
    SpecialistType,
)


@runtime_checkable
class SpecialistManagerContract(Protocol):
    """Contract for specialist management and dynamic selection.
    
    Handles specialist selection decisions, switching operations,
    rule evaluation, and configuration management.
    """

    async def select_specialist(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        context_requirements: list[str] | None = None,
        current_specialist: SpecialistType | None = None,
    ) -> SpecialistDecisionResult:
        """Select optimal specialist for a given task.
        
        Args:
            task_id: Unique identifier for the task
            task_description: Full description of what needs to be done
            task_complexity: Complexity classification (simple/medium/complex)
            context_requirements: Special requirements from context
            current_specialist: Currently active specialist
            
        Returns:
            Complete specialist decision with configuration
        """
        ...

    async def switch_specialist(
        self,
        session_id: str,
        from_specialist: SpecialistType,
        to_specialist: SpecialistType,
        trigger: str,
        rationale: str,
        carry_over_context: str = "",
    ) -> SpecialistSwitchContext:
        """Switch from one specialist to another.
        
        Args:
            session_id: Unique session identifier
            from_specialist: Currently active specialist
            to_specialist: Target specialist to switch to
            trigger: What triggered the switch
            rationale: Reason for the switch
            carry_over_context: Context to preserve
            
        Returns:
            Context for the specialist switch
        """
        ...

    async def configure_specialist(
        self,
        specialist: SpecialistType,
        task_complexity: str,
        custom_overrides: dict | None = None,
    ) -> SpecialistConfiguration:
        """Configure specialist for specific task complexity.
        
        Args:
            specialist: The specialist type to configure
            task_complexity: Task complexity level
            custom_overrides: Optional custom configuration overrides
            
        Returns:
            Complete specialist configuration
        """
        ...

    async def evaluate_specialist_performance(
        self,
        specialist: SpecialistType,
        task_id: str,
        performance_metrics: dict,
    ) -> float:
        """Evaluate specialist performance on completed task.
        
        Args:
            specialist: The specialist that performed the task
            task_id: Identifier of the completed task
            performance_metrics: Performance data (efficiency, quality, etc.)
            
        Returns:
            Performance score (0.0 to 1.0)
        """
        ...

    async def add_selection_rule(
        self,
        rule: SpecialistSelectionRule,
    ) -> None:
        """Add a new specialist selection rule.
        
        Args:
            rule: The rule to add to the selection engine
        """
        ...

    async def remove_selection_rule(
        self,
        rule_name: str,
    ) -> None:
        """Remove a specialist selection rule.
        
        Args:
            rule_name: Name of the rule to remove
        """
        ...

    async def list_available_specialists(
        self,
        include_core: bool = True,
        include_specialized: bool = True,
    ) -> list[SpecialistType]:
        """List all available specialists.
        
        Args:
            include_core: Whether to include core specialists
            include_specialized: Whether to include specialized specialists
            
        Returns:
            List of available specialist types
        """
        ...

    async def get_specialist_stats(
        self,
        specialist: SpecialistType | None = None,
        time_range: tuple[str, str] | None = None,
    ) -> dict:
        """Get statistics about specialist usage and performance.
        
        Args:
            specialist: Specific specialist to get stats for (None for all)
            time_range: Time range for stats (start, end) in ISO format
            
        Returns:
            Dictionary with usage and performance statistics
        """
        ...

    async def reset_specialist_cache(
        self,
        specialist: SpecialistType | None = None,
    ) -> None:
        """Reset specialist selection cache.
        
        Args:
            specialist: Specific specialist to reset cache for (None for all)
        """
        ...

    async def validate_specialist_configuration(
        self,
        configuration: SpecialistConfiguration,
    ) -> tuple[bool, list[str]]:
        """Validate specialist configuration.
        
        Args:
            configuration: Configuration to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        ...

    async def get_specialist_recommendations(
        self,
        task_description: str,
        context_requirements: list[str] | None = None,
        limit: int = 5,
    ) -> list[tuple[SpecialistType, float, str]]:
        """Get specialist recommendations for a task.
        
        Args:
            task_description: Description of the task
            context_requirements: Special requirements
            limit: Maximum number of recommendations
            
        Returns:
            List of (specialist, confidence, reason) tuples
        """
        ...

    async def export_specialist_rules(
        self,
        format: str = "json",
    ) -> str:
        """Export specialist selection rules.
        
        Args:
            format: Export format (json, yaml, csv)
            
        Returns:
            Serialized rules in requested format
        """
        ...

    async def import_specialist_rules(
        self,
        rules_data: str,
        format: str = "json",
        merge_strategy: str = "replace",
    ) -> dict:
        """Import specialist selection rules.
        
        Args:
            rules_data: Serialized rules data
            format: Import format (json, yaml, csv)
            merge_strategy: How to merge with existing rules (replace, merge, update)
            
        Returns:
            Import result with statistics
        """
        ...
