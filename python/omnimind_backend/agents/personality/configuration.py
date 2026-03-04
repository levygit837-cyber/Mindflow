"""Configuration management for personality system.

Provides personality configuration building and management
for different personality types and complexities.
"""

from __future__ import annotations

from typing import Dict, Any, List

from omnimind_backend.schemas.orchestration.personality import (
    PersonalityType,
    TaskComplexity,
    PersonalityConfiguration,
    PersonalitySelection,
    PersonalityDecisionResult,
)
from omnimind_backend.agents._base import AgentType, ThinkingLevel, SandboxMode
from omnimind_backend.config.agents import get_agent_config
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PersonalityConfigurationBuilder:
    """Builds personality configurations based on type and complexity."""
    
    def __init__(self):
        self.config = get_agent_config()
    
    def build_configuration(
        self,
        personality: PersonalityType,
        complexity: TaskComplexity,
    ) -> PersonalityConfiguration:
        """Build personality configuration based on type and complexity."""
        try:
            base_config = self._get_base_configuration(personality)
            enhanced_config = self._enhance_for_complexity(base_config, complexity)
            
            _logger.debug(
                "personality_configuration_built",
                personality=personality,
                complexity=complexity,
                agent_type=enhanced_config.agent_type,
                thinking_level=enhanced_config.thinking_level,
            )
            
            return enhanced_config
        
        except Exception as e:
            _logger.error("configuration_build_failed", personality=personality, error=str(e))
            # Fallback to core configuration
            return self._get_fallback_configuration()
    
    def _get_base_configuration(self, personality: PersonalityType) -> PersonalityConfiguration:
        """Get base configuration for personality type."""
        configurations = {
            PersonalityType.CORE: PersonalityConfiguration(
                personality=personality,
                agent_type=AgentType.ANALYST,
                prompt_segments=["core", "read"],
                tools=["CODE_ANALYSIS", "FILESYSTEM"],
                thinking_level=ThinkingLevel.MEDIUM,
                sandbox_mode=SandboxMode.NONE,
                max_iterations=1,
            ),
            
            PersonalityType.SECURITY_GUARD: PersonalityConfiguration(
                personality=personality,
                agent_type=AgentType.ANALYST,
                prompt_segments=["core", "security_guard"],
                tools=["CODE_ANALYSIS", "FILESYSTEM"],
                thinking_level=ThinkingLevel.HIGH,
                sandbox_mode=SandboxMode.READ_ONLY,
                max_iterations=1,
            ),
            
            PersonalityType.CRITIC: PersonalityConfiguration(
                personality=personality,
                agent_type=AgentType.ANALYST,
                prompt_segments=["core", "critic"],
                tools=["CODE_ANALYSIS"],
                thinking_level=ThinkingLevel.HIGH,
                sandbox_mode=SandboxMode.NONE,
                max_iterations=1,
            ),
            
            PersonalityType.BRAINSTORM: PersonalityConfiguration(
                personality=personality,
                agent_type=AgentType.ANALYST,
                prompt_segments=["core", "brainstorm"],
                tools=["CODE_ANALYSIS"],
                thinking_level=ThinkingLevel.HIGH,
                sandbox_mode=SandboxMode.NONE,
                max_iterations=1,
            ),
            
            PersonalityType.ARCH_TECH: PersonalityConfiguration(
                personality=personality,
                agent_type=AgentType.CODER,
                prompt_segments=["core", "arch_tech"],
                tools=["FILESYSTEM", "CODE_ANALYSIS"],
                thinking_level=ThinkingLevel.HIGH,
                sandbox_mode=SandboxMode.NONE,
                max_iterations=1,
            ),
            
            PersonalityType.DEEP_ITERATION: PersonalityConfiguration(
                personality=personality,
                agent_type=AgentType.ANALYST,
                prompt_segments=["core", "read", "deep_iteration"],
                tools=["CODE_ANALYSIS", "FILESYSTEM"],
                thinking_level=ThinkingLevel.HIGH,
                sandbox_mode=SandboxMode.NONE,
                max_iterations=2,  # Default for medium complexity
            ),
        }
        
        return configurations.get(personality, configurations[PersonalityType.CORE])
    
    def _enhance_for_complexity(
        self,
        base_config: PersonalityConfiguration,
        complexity: TaskComplexity,
    ) -> PersonalityConfiguration:
        """Enhance configuration based on task complexity."""
        if complexity == TaskComplexity.SIMPLE:
            return self._enhance_for_simple(base_config)
        elif complexity == TaskComplexity.MEDIUM:
            return self._enhance_for_medium(base_config)
        elif complexity == TaskComplexity.COMPLEX:
            return self._enhance_for_complex(base_config)
        else:
            return base_config
    
    def _enhance_for_simple(self, config: PersonalityConfiguration) -> PersonalityConfiguration:
        """Enhance configuration for simple tasks."""
        # Simple tasks get reduced thinking and iterations
        return PersonalityConfiguration(
            personality=config.personality,
            agent_type=config.agent_type,
            prompt_segments=config.prompt_segments,
            tools=config.tools,
            thinking_level=self._reduce_thinking_level(config.thinking_level),
            sandbox_mode=config.sandbox_mode,
            max_iterations=1,
        )
    
    def _enhance_for_medium(self, config: PersonalityConfiguration) -> PersonalityConfiguration:
        """Enhance configuration for medium tasks."""
        # Medium tasks get standard configuration
        return PersonalityConfiguration(
            personality=config.personality,
            agent_type=config.agent_type,
            prompt_segments=config.prompt_segments,
            tools=config.tools,
            thinking_level=config.thinking_level,
            sandbox_mode=config.sandbox_mode,
            max_iterations=config.max_iterations or 2,
        )
    
    def _enhance_for_complex(self, config: PersonalityConfiguration) -> PersonalityConfiguration:
        """Enhance configuration for complex tasks."""
        # Complex tasks get enhanced thinking and more iterations
        enhanced_iterations = max(config.max_iterations or 2, 3)
        
        return PersonalityConfiguration(
            personality=config.personality,
            agent_type=config.agent_type,
            prompt_segments=config.prompt_segments,
            tools=config.tools,
            thinking_level=ThinkingLevel.HIGH,  # Force high for complex tasks
            sandbox_mode=config.sandbox_mode,
            max_iterations=enhanced_iterations,
        )
    
    def _reduce_thinking_level(self, level: ThinkingLevel) -> ThinkingLevel:
        """Reduce thinking level by one step."""
        if level == ThinkingLevel.HIGH:
            return ThinkingLevel.MEDIUM
        elif level == ThinkingLevel.MEDIUM:
            return ThinkingLevel.LOW
        else:
            return ThinkingLevel.NONE
    
    def _get_fallback_configuration(self) -> PersonalityConfiguration:
        """Get fallback configuration for errors."""
        return PersonalityConfiguration(
            personality=PersonalityType.CORE,
            agent_type=AgentType.ANALYST,
            prompt_segments=["core", "read"],
            tools=["CODE_ANALYSIS"],
            thinking_level=ThinkingLevel.MEDIUM,
            sandbox_mode=SandboxMode.NONE,
            max_iterations=1,
        )


class DelegationTaskBuilder:
    """Builds delegation tasks for personality configurations."""
    
    def build_delegation_task(
        self,
        selection: PersonalitySelection,
        configuration: PersonalityConfiguration,
        task_description: str,
    ) -> Dict[str, Any]:
        """Build delegation task configured for selected personality."""
        return {
            "agent": configuration.agent_type,
            "objective": task_description,
            "tools": configuration.tools,
            "thinking_level": configuration.thinking_level,
            "sandbox_mode": configuration.sandbox_mode,
            "priority": "NORMAL",
            "keep_context": True,
            "max_iterations": configuration.max_iterations,
            "personality": configuration.personality,
            "prompt_segments": configuration.prompt_segments,
            "task_complexity": selection.task_complexity,
            "requires_specialization": selection.requires_specialization,
            "context_requirements": selection.context_requirements,
        }
    
    def build_switch_context(
        self,
        session_id: str,
        from_personality: PersonalityType,
        to_personality: PersonalityType,
        trigger: str,
        rationale: str,
        carry_over_context: str = "",
    ) -> Dict[str, Any]:
        """Build personality switch context."""
        return {
            "session_id": session_id,
            "from_personality": from_personality,
            "to_personality": to_personality,
            "switch_trigger": trigger,
            "carry_over_context": carry_over_context,
            "switch_rationale": rationale,
            "expected_benefit": self._estimate_switch_benefit(from_personality, to_personality),
            "timestamp": self._get_timestamp(),
        }
    
    def _estimate_switch_benefit(
        self,
        from_personality: PersonalityType,
        to_personality: PersonalityType,
    ) -> str:
        """Estimate benefit of personality switch."""
        if from_personality == to_personality:
            return "No change needed"
        
        benefits = {
            (PersonalityType.CORE, PersonalityType.SECURITY_GUARD): "Enhanced security focus",
            (PersonalityType.CORE, PersonalityType.CRITIC): "Improved code quality assessment",
            (PersonalityType.CORE, PersonalityType.BRAINSTORM): "Enhanced creative exploration",
            (PersonalityType.CORE, PersonalityType.ARCH_TECH): "Better architectural decisions",
            (PersonalityType.CORE, PersonalityType.DEEP_ITERATION): "More thorough analysis",
            (PersonalityType.ANALYST, PersonalityType.SECURITY_GUARD): "Security-focused analysis",
            (PersonalityType.ANALYST, PersonalityType.CRITIC): "Quality-focused evaluation",
            (PersonalityType.ANALYST, PersonalityType.BRAINSTORM): "Creative problem-solving",
            (PersonalityType.CODER, PersonalityType.ARCH_TECH): "Architecture-aware implementation",
        }
        
        return benefits.get((from_personality, to_personality), "Optimized task handling")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()


# Global builders
_config_builder: PersonalityConfigurationBuilder | None = None
_task_builder: DelegationTaskBuilder | None = None


def get_personality_config_builder() -> PersonalityConfigurationBuilder:
    """Get the global personality configuration builder."""
    global _config_builder
    if _config_builder is None:
        _config_builder = PersonalityConfigurationBuilder()
    return _config_builder


def get_delegation_task_builder() -> DelegationTaskBuilder:
    """Get the global delegation task builder."""
    global _task_builder
    if _task_builder is None:
        _task_builder = DelegationTaskBuilder()
    return _task_builder
