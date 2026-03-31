"""Specialist selector service for Orchestrator dynamic specialist switching.

Implements intelligent specialist selection based on task analysis,
context requirements, and configurable heuristics.
Refactored to use modular architecture with dependency injection.
"""

from __future__ import annotations

import hashlib
from typing import Any

from mindflow_backend.agents.specialists.cache import SpecialistCache, get_specialist_cache
from mindflow_backend.agents.specialists.configuration import (
    DelegationTaskBuilder,
    SpecialistConfigurationBuilder,
    get_delegation_task_builder,
    get_specialist_config_builder,
)
from mindflow_backend.agents.specialists.rule_engine import (
    SpecialistCandidate,
    SpecialistRuleEngine,
    get_specialist_rule_engine,
)
from mindflow_backend.exceptions import SpecialistSelectionError
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.interfaces.agents import SpecialistSelector as SpecialistSelectorInterface
from mindflow_backend.schemas.orchestration.specialists import (
    SpecialistDecisionResult,
    SpecialistSelection,
    SpecialistSwitchContext,
    SpecialistSwitchTrigger,
    SpecialistType,
    SpecializationRequirement,
    TaskComplexity,
)

_logger = get_logger(__name__)


class SpecialistSelector(SpecialistSelectorInterface):
    """Intelligent specialist selection engine.
    
    Analyzes tasks and selects optimal specialist configuration
    based on heuristics, context, and performance history.
    Refactored to use modular components.
    """
    
    def __init__(
        self,
        rule_engine: SpecialistRuleEngine | None = None,
        cache: SpecialistCache | None = None,
        config_builder: SpecialistConfigurationBuilder | None = None,
        task_builder: DelegationTaskBuilder | None = None,
    ) -> None:
        """Initialize specialist selector with modular components."""
        self.rule_engine = rule_engine or get_specialist_rule_engine()
        self.cache = cache or get_specialist_cache()
        self.config_builder = config_builder or get_specialist_config_builder()
        self.task_builder = task_builder or get_delegation_task_builder()
        
        _logger.info("specialist_selector_initialized_modular")
    
    def select_specialist(
        self,
        task_id: str,
        task_description: str,
        task_complexity: TaskComplexity,
        context_requirements: list[str] | None = None,
        current_specialist: SpecialistType | None = None,
    ) -> SpecialistDecisionResult:
        """
        Select optimal specialist for a given task.
        
        Args:
            task_id: Unique identifier for the task
            task_description: Full description of what needs to be done
            task_complexity: Complexity classification
            context_requirements: Special requirements from context
            current_specialist: Currently active specialist
            
        Returns:
            Complete specialist decision with configuration
        """
        try:
            _logger.info(
                "specialist_selection_started_modular",
                task_id=task_id,
                complexity=task_complexity,
                current_specialist=current_specialist,
            )
            
            # Check cache first
            task_signature = self._generate_task_signature(
                task_description, task_complexity, context_requirements or []
            )
            
            cached_decision = self.cache.get_decision(task_signature)
            if cached_decision:
                _logger.info("specialist_selection_cache_hit", task_signature=task_signature)
                return self._build_cached_result(cached_decision, task_id)
            
            # Analyze task requirements
            specialization = self._detect_specialization(task_description, context_requirements or [])
            
            # Apply selection rules using rule engine
            candidates = self.rule_engine.evaluate(
                task_description, task_complexity, specialization
            )
            
            # Choose best candidate
            selected = self._select_best_candidate(candidates, current_specialist)
            
            # Build decision using configuration builder
            selection = self._build_selection(
                task_id, task_description, task_complexity,
                specialization, context_requirements, selected
            )
            
            # Build configuration using config builder
            configuration = self.config_builder.build_configuration(
                selected.specialist, task_complexity
            )
            
            # Build delegation task using task builder
            delegation_task = self.task_builder.build_delegation_task(
                selection, configuration, task_description
            )
            
            result = SpecialistDecisionResult(
                selection=selection,
                configuration=configuration,
                delegation_task=delegation_task,
                estimated_efficiency_gain=selected.estimated_efficiency_gain,
                fallback_used=len(candidates) == 0,
            )
            
            # Cache the decision
            self.cache.set_decision(
                task_signature, 
                self._create_cache_entry(selected, result),
                ttl=3600  # 1 hour
            )
            
            _logger.info(
                "specialist_selection_completed_modular",
                selected_specialist=selected.specialist,
                confidence=selected.confidence,
                estimated_efficiency_gain=selected.estimated_efficiency_gain,
            )
            
            return result
        
        except Exception as e:
            _logger.error("specialist_selection_failed", task_id=task_id, error=str(e))
            raise SpecialistSelectionError(
                f"Specialist selection failed: {e}",
                task_id=task_id,
                task_description=task_description
            )
    
    def create_switch_context(
        self,
        session_id: str,
        from_specialist: SpecialistType,
        to_specialist: SpecialistType,
        trigger: SpecialistSwitchTrigger,
        rationale: str,
        carry_over_context: str = "",
    ) -> SpecialistSwitchContext:
        """Create context for specialist switching."""
        return self.task_builder.build_switch_context(
            session_id, from_specialist, to_specialist,
            trigger.value, rationale, carry_over_context
        )
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        return self.cache.get_stats()
    
    def add_rule(self, rule: dict[str, Any]) -> None:
        """Add a custom specialist selection rule."""
        self.rule_engine.add_rule(rule)
        _logger.info("custom_rule_added_to_selector", rule=rule.get("name"))
    
    # -----------------------------------------------------------------------
    # Private Helper Methods
    # -----------------------------------------------------------------------
    
    def _detect_specialization(
        self, task_description: str, context_requirements: list[str]
    ) -> SpecializationRequirement:
        """Detect required specialization from task and context."""
        description_lower = task_description.lower()
        context_lower = " ".join(context_requirements).lower()
        
        # Security keywords
        if any(keyword in description_lower or keyword in context_lower 
               for keyword in ["security", "vulnerability", "audit", "auth", "permission"]):
            return SpecializationRequirement.SECURITY
        
        # Architecture keywords
        if any(keyword in description_lower or keyword in context_lower 
               for keyword in ["architecture", "design", "structure", "pattern"]):
            return SpecializationRequirement.ARCHITECTURE
        
        # Code review keywords
        if any(keyword in description_lower or keyword in context_lower 
               for keyword in ["review", "critique", "evaluate", "quality"]):
            return SpecializationRequirement.CODE_REVIEW
        
        # Brainstorm / ideation keywords
        if any(keyword in description_lower or keyword in context_lower 
               for keyword in ["brainstorm", "creative", "alternative", "explore"]):
            return SpecializationRequirement.ANALYSIS
        
        # Implementation keywords
        if any(keyword in description_lower or keyword in context_lower 
               for keyword in ["implement", "code", "fix", "build", "write"]):
            return SpecializationRequirement.IMPLEMENTATION
        
        # Default to analysis
        return SpecializationRequirement.ANALYSIS
    
    def _select_best_candidate(
        self, candidates: list[SpecialistCandidate], 
        current_specialist: SpecialistType | None
    ) -> SpecialistCandidate:
        """Select best specialist from candidates."""
        if not candidates:
            # Fallback to core specialist
            return SpecialistCandidate(
                specialist=SpecialistType.CORE,
                rule_name="fallback",
                confidence=0.5,
                reason="Fallback to core specialist",
                estimated_tokens_saved=0,
                estimated_efficiency_gain=0.0,
                priority=10,
            )
        
        best = candidates[0]
        
        # Prefer specialist switches only if significant benefit
        if (current_specialist and 
            best.specialist == current_specialist and 
            len(candidates) > 1):
            
            # Look for better alternative
            for candidate in candidates[1:]:
                if (candidate.confidence > best.confidence + 0.1 and 
                    candidate.specialist != current_specialist):
                    best = candidate
                    break
        
        return best
    
    def _build_selection(
        self,
        task_id: str,
        task_description: str,
        task_complexity: TaskComplexity,
        specialization: SpecializationRequirement,
        context_requirements: list[str],
        selected: SpecialistCandidate,
    ) -> SpecialistSelection:
        """Build specialist selection object."""
        return SpecialistSelection(
            task_id=task_id,
            task_complexity=task_complexity,
            requires_specialization=specialization,
            context_requirements=context_requirements,
            selected_specialist=selected.specialist,
            alternative_specialists=[],  # Will be populated if needed
            specialist_switch_reason=selected.reason,
            confidence_score=selected.confidence,
            performance_expectation=selected.reason,
            estimated_tokens_saved=selected.estimated_tokens_saved,
        )
    
    def _generate_task_signature(
        self, task_description: str, complexity: TaskComplexity, 
        context_requirements: list[str]
    ) -> str:
        """Generate signature for cache lookup."""
        content = f"{task_description}:{complexity}:{':'.join(sorted(context_requirements))}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _build_cached_result(
        self, cached_decision: Any, task_id: str
    ) -> SpecialistDecisionResult:
        """Build result from cached decision."""
        # For now, create a simple result from cached decision
        # In practice, this would reconstruct the full result
        return SpecialistDecisionResult(
            selection=SpecialistSelection(
                task_id=task_id,
                task_complexity=TaskComplexity.MEDIUM,
                selected_specialist=getattr(cached_decision, 'specialist', SpecialistType.CORE),
                specialist_switch_reason="Cached decision",
                confidence_score=getattr(cached_decision, 'confidence', 0.5),
                estimated_tokens_saved=getattr(cached_decision, 'tokens_saved', 0),
            ),
            configuration=self.config_builder.build_configuration(
                getattr(cached_decision, 'specialist', SpecialistType.CORE),
                TaskComplexity.MEDIUM
            ),
            delegation_task={},
            estimated_efficiency_gain=0.1,
            fallback_used=False,
        )
    
    def _create_cache_entry(self, selected: SpecialistCandidate, result: SpecialistDecisionResult) -> dict[str, Any]:
        """Create cache entry from selected candidate and result."""
        return {
            "specialist": selected.specialist,
            "confidence": selected.confidence,
            "tokens_saved": selected.estimated_tokens_saved,
            "efficiency_gain": selected.estimated_efficiency_gain,
            "rule_name": selected.rule_name,
            "timestamp": self._get_timestamp(),
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import UTC, datetime
        return datetime.now(UTC).isoformat()


# Global instance for backward compatibility
_specialist_selector: SpecialistSelector | None = None


def get_specialist_selector() -> SpecialistSelector:
    """Get or create the global specialist selector instance."""
    global _specialist_selector
    if _specialist_selector is None:
        _specialist_selector = SpecialistSelector()
    return _specialist_selector
