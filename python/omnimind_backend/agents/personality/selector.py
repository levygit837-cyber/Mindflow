"""Personality selector service for Orchestrator dynamic personality switching.

Implements intelligent personality selection based on task analysis,
context requirements, and configurable heuristics.
Refactored to use modular architecture with dependency injection.
"""

from __future__ import annotations

import hashlib
from typing import Any

from omnimind_backend.agents.interfaces.core import PersonalitySelector as PersonalitySelectorInterface
from omnimind_backend.agents.core.exceptions import PersonalitySelectionError
from omnimind_backend.agents.personality.rule_engine import (
    get_personality_rule_engine,
    PersonalityRuleEngine,
    PersonalityCandidate,
)
from omnimind_backend.agents.personality.cache import get_personality_cache, PersonalityCache
from omnimind_backend.agents.personality.configuration import (
    get_personality_config_builder,
    get_delegation_task_builder,
    PersonalityConfigurationBuilder,
    DelegationTaskBuilder,
)
from omnimind_backend.schemas.orchestration.personality import (
    PersonalitySelection,
    PersonalitySwitchContext,
    PersonalityConfiguration,
    PersonalityDecisionResult,
    PersonalityType,
    TaskComplexity,
    SpecializationRequirement,
    PersonalitySwitchTrigger,
)
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PersonalitySelector(PersonalitySelectorInterface):
    """Intelligent personality selection engine.
    
    Analyzes tasks and selects optimal personality configuration
    based on heuristics, context, and performance history.
    Refactored to use modular components.
    """
    
    def __init__(
        self,
        rule_engine: PersonalityRuleEngine | None = None,
        cache: PersonalityCache | None = None,
        config_builder: PersonalityConfigurationBuilder | None = None,
        task_builder: DelegationTaskBuilder | None = None,
    ) -> None:
        """Initialize personality selector with modular components."""
        self.rule_engine = rule_engine or get_personality_rule_engine()
        self.cache = cache or get_personality_cache()
        self.config_builder = config_builder or get_personality_config_builder()
        self.task_builder = task_builder or get_delegation_task_builder()
        
        _logger.info("personality_selector_initialized_modular")
    
    def select_personality(
        self,
        task_id: str,
        task_description: str,
        task_complexity: TaskComplexity,
        context_requirements: list[str] | None = None,
        current_personality: PersonalityType | None = None,
    ) -> PersonalityDecisionResult:
        """
        Select optimal personality for a given task.
        
        Args:
            task_id: Unique identifier for the task
            task_description: Full description of what needs to be done
            task_complexity: Complexity classification
            context_requirements: Special requirements from context
            current_personality: Currently active personality
            
        Returns:
            Complete personality decision with configuration
        """
        try:
            _logger.info(
                "personality_selection_started_modular",
                task_id=task_id,
                complexity=task_complexity,
                current_personality=current_personality,
            )
            
            # Check cache first
            task_signature = self._generate_task_signature(
                task_description, task_complexity, context_requirements or []
            )
            
            cached_decision = self.cache.get_decision(task_signature)
            if cached_decision:
                _logger.info("personality_selection_cache_hit", task_signature=task_signature)
                return self._build_cached_result(cached_decision, task_id)
            
            # Analyze task requirements
            specialization = self._detect_specialization(task_description, context_requirements or [])
            
            # Apply selection rules using rule engine
            candidates = self.rule_engine.evaluate(
                task_description, task_complexity, specialization
            )
            
            # Choose best candidate
            selected = self._select_best_candidate(candidates, current_personality)
            
            # Build decision using configuration builder
            selection = self._build_selection(
                task_id, task_description, task_complexity,
                specialization, context_requirements, selected
            )
            
            # Build configuration using config builder
            configuration = self.config_builder.build_configuration(
                selected.personality, task_complexity
            )
            
            # Build delegation task using task builder
            delegation_task = self.task_builder.build_delegation_task(
                selection, configuration, task_description
            )
            
            result = PersonalityDecisionResult(
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
                "personality_selection_completed_modular",
                selected_personality=selected.personality,
                confidence=selected.confidence,
                estimated_efficiency_gain=selected.estimated_efficiency_gain,
            )
            
            return result
        
        except Exception as e:
            _logger.error("personality_selection_failed", task_id=task_id, error=str(e))
            raise PersonalitySelectionError(
                f"Personality selection failed: {e}",
                task_id=task_id,
                task_description=task_description
            )
    
    def create_switch_context(
        self,
        session_id: str,
        from_personality: PersonalityType,
        to_personality: PersonalityType,
        trigger: PersonalitySwitchTrigger,
        rationale: str,
        carry_over_context: str = "",
    ) -> PersonalitySwitchContext:
        """Create context for personality switching."""
        return self.task_builder.build_switch_context(
            session_id, from_personality, to_personality,
            trigger.value, rationale, carry_over_context
        )
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        return self.cache.get_stats()
    
    def add_rule(self, rule: dict[str, Any]) -> None:
        """Add a custom personality selection rule."""
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
        
        # Creative keywords
        if any(keyword in description_lower or keyword in context_lower 
               for keyword in ["brainstorm", "creative", "alternative", "explore"]):
            return SpecializationRequirement.CREATIVE
        
        # Implementation keywords
        if any(keyword in description_lower or keyword in context_lower 
               for keyword in ["implement", "code", "fix", "build", "write"]):
            return SpecializationRequirement.IMPLEMENTATION
        
        # Default to analysis
        return SpecializationRequirement.ANALYSIS
    
    def _select_best_candidate(
        self, candidates: list[PersonalityCandidate], 
        current_personality: PersonalityType | None
    ) -> PersonalityCandidate:
        """Select best personality from candidates."""
        if not candidates:
            # Fallback to core personality
            return PersonalityCandidate(
                personality=PersonalityType.CORE,
                rule_name="fallback",
                confidence=0.5,
                reason="Fallback to core personality",
                estimated_tokens_saved=0,
                estimated_efficiency_gain=0.0,
                priority=10,
            )
        
        best = candidates[0]
        
        # Prefer personality switches only if significant benefit
        if (current_personality and 
            best.personality == current_personality and 
            len(candidates) > 1):
            
            # Look for better alternative
            for candidate in candidates[1:]:
                if (candidate.confidence > best.confidence + 0.1 and 
                    candidate.personality != current_personality):
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
        selected: PersonalityCandidate,
    ) -> PersonalitySelection:
        """Build personality selection object."""
        return PersonalitySelection(
            task_id=task_id,
            task_complexity=task_complexity,
            requires_specialization=specialization,
            context_requirements=context_requirements,
            selected_personality=selected.personality,
            alternative_personalities=[],  # Will be populated if needed
            personality_switch_reason=selected.reason,
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
    ) -> PersonalityDecisionResult:
        """Build result from cached decision."""
        # For now, create a simple result from cached decision
        # In practice, this would reconstruct the full result
        return PersonalityDecisionResult(
            selection=PersonalitySelection(
                task_id=task_id,
                task_complexity=TaskComplexity.MEDIUM,
                selected_personality=getattr(cached_decision, 'personality', PersonalityType.CORE),
                personality_switch_reason="Cached decision",
                confidence_score=getattr(cached_decision, 'confidence', 0.5),
                estimated_tokens_saved=getattr(cached_decision, 'tokens_saved', 0),
            ),
            configuration=self.config_builder.build_configuration(
                getattr(cached_decision, 'personality', PersonalityType.CORE),
                TaskComplexity.MEDIUM
            ),
            delegation_task={},
            estimated_efficiency_gain=0.1,
            fallback_used=False,
        )
    
    def _create_cache_entry(self, selected: PersonalityCandidate, result: PersonalityDecisionResult) -> dict[str, Any]:
        """Create cache entry from selected candidate and result."""
        return {
            "personality": selected.personality,
            "confidence": selected.confidence,
            "tokens_saved": selected.estimated_tokens_saved,
            "efficiency_gain": selected.estimated_efficiency_gain,
            "rule_name": selected.rule_name,
            "timestamp": self._get_timestamp(),
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()


# Global instance for backward compatibility
_personality_selector: PersonalitySelector | None = None


def get_personality_selector() -> PersonalitySelector:
    """Get or create the global personality selector instance."""
    global _personality_selector
    if _personality_selector is None:
        _personality_selector = PersonalitySelector()
    return _personality_selector
