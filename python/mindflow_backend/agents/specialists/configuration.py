"""Configuration management for specialist system.

Provides specialist configuration building and management
for different specialist types and complexities.
"""

from __future__ import annotations

from typing import Dict, Any

from mindflow_backend.schemas.orchestration.specialists import (
    SpecialistType,
    TaskComplexity,
    SpecialistConfiguration,
    SpecialistSelection,
    SpecialistDecisionResult,
)
from mindflow_backend.agents._base import AgentType, ThinkingLevel, SandboxMode
from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
from mindflow_backend.config.agents import get_agent_config
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class SpecialistConfigurationBuilder:
    """Builds specialist configurations based on type and complexity."""
    
    def __init__(self):
        self.config = get_agent_config()
    
    def build_configuration(
        self,
        specialist: SpecialistType,
        complexity: TaskComplexity,
    ) -> SpecialistConfiguration:
        """Build specialist configuration based on type and complexity."""
        try:
            base_config = self._get_base_configuration(specialist)
            enhanced_config = self._enhance_for_complexity(base_config, complexity)
            
            _logger.debug(
                "specialist_configuration_built",
                specialist=specialist,
                complexity=complexity,
                agent_type=enhanced_config.agent_type,
                thinking_level=enhanced_config.thinking_level,
            )
            
            return enhanced_config
        
        except Exception as e:
            _logger.error("configuration_build_failed", specialist=specialist, error=str(e))
            # Fallback to core configuration
            return self._get_fallback_configuration()
    
    def _get_base_configuration(self, specialist: SpecialistType) -> SpecialistConfiguration:
        """Get base configuration for specialist type."""
        policy_keys = {
            SpecialistType.CORE: "analyst",
            SpecialistType.SECURITY_GUARD: "analyst:security_guard",
            SpecialistType.CRITIC: "analyst:critic",
            SpecialistType.BRAINSTORM: "analyst:brainstorm",
            SpecialistType.ARCH_TECH: "coder:arch_tech",
            SpecialistType.DEEP_ITERATION: "analyst:deep_iteration",
        }
        prompt_segments = {
            SpecialistType.CORE: ["core", "read"],
            SpecialistType.SECURITY_GUARD: ["core", "security_guard"],
            SpecialistType.CRITIC: ["core", "critic"],
            SpecialistType.BRAINSTORM: ["core", "brainstorm"],
            SpecialistType.ARCH_TECH: ["core", "arch_tech"],
            SpecialistType.DEEP_ITERATION: ["deep_iteration"],
        }

        key = policy_keys.get(specialist, "analyst")
        policy = get_agent_runtime_policy(agent_id=key)

        return SpecialistConfiguration(
            specialist=specialist,
            agent_type=policy.agent_role,
            prompt_segments=prompt_segments.get(specialist, ["core", "read"]),
            tools=[tool.name for tool in policy.tools],
            thinking_level=policy.thinking_level,
            sandbox_mode=policy.sandbox,
            max_iterations=policy.max_iterations,
        )
    
    def _enhance_for_complexity(
        self,
        base_config: SpecialistConfiguration,
        complexity: TaskComplexity,
    ) -> SpecialistConfiguration:
        """Enhance configuration based on task complexity."""
        if complexity == TaskComplexity.SIMPLE:
            return self._enhance_for_simple(base_config)
        elif complexity == TaskComplexity.MEDIUM:
            return self._enhance_for_medium(base_config)
        elif complexity == TaskComplexity.COMPLEX:
            return self._enhance_for_complex(base_config)
        else:
            return base_config
    
    def _enhance_for_simple(self, config: SpecialistConfiguration) -> SpecialistConfiguration:
        """Enhance configuration for simple tasks."""
        # Simple tasks get reduced thinking and iterations
        return SpecialistConfiguration(
            specialist=config.specialist,
            agent_type=config.agent_type,
            prompt_segments=config.prompt_segments,
            tools=config.tools,
            thinking_level=self._reduce_thinking_level(config.thinking_level),
            sandbox_mode=config.sandbox_mode,
            max_iterations=1,
        )
    
    def _enhance_for_medium(self, config: SpecialistConfiguration) -> SpecialistConfiguration:
        """Enhance configuration for medium tasks."""
        # Medium tasks get standard configuration
        return SpecialistConfiguration(
            specialist=config.specialist,
            agent_type=config.agent_type,
            prompt_segments=config.prompt_segments,
            tools=config.tools,
            thinking_level=config.thinking_level,
            sandbox_mode=config.sandbox_mode,
            max_iterations=config.max_iterations or 2,
        )
    
    def _enhance_for_complex(self, config: SpecialistConfiguration) -> SpecialistConfiguration:
        """Enhance configuration for complex tasks."""
        # Complex tasks get enhanced thinking and more iterations
        enhanced_iterations = max(config.max_iterations or 2, 3)
        
        return SpecialistConfiguration(
            specialist=config.specialist,
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
    
    def _get_fallback_configuration(self) -> SpecialistConfiguration:
        """Get fallback configuration for errors."""
        return SpecialistConfiguration(
            specialist=SpecialistType.CORE,
            agent_type=AgentType.ANALYST,
            prompt_segments=["core", "read"],
            tools=["CODE_ANALYSIS"],
            thinking_level=ThinkingLevel.MEDIUM,
            sandbox_mode=SandboxMode.NONE,
            max_iterations=1,
        )


class DelegationTaskBuilder:
    """Builds delegation tasks for specialist configurations."""
    
    def build_delegation_task(
        self,
        selection: SpecialistSelection,
        configuration: SpecialistConfiguration,
        task_description: str,
    ) -> Dict[str, Any]:
        """Build delegation task configured for selected specialist."""
        return {
            "agent": configuration.agent_type,
            "agent_id": (
                configuration.agent_type
                if configuration.specialist in {SpecialistType.CORE, SpecialistType.ANALYST, SpecialistType.CODER}
                else f"{configuration.agent_type}:{configuration.specialist}"
            ),
            "objective": task_description,
            "tools": configuration.tools,
            "thinking_level": configuration.thinking_level,
            "sandbox_mode": configuration.sandbox_mode,
            "priority": "NORMAL",
            "keep_context": True,
            "max_iterations": configuration.max_iterations,
            "specialist": configuration.specialist,
            "prompt_segments": configuration.prompt_segments,
            "task_complexity": selection.task_complexity,
            "requires_specialization": selection.requires_specialization,
            "context_requirements": selection.context_requirements,
        }
    
    def build_switch_context(
        self,
        session_id: str,
        from_specialist: SpecialistType,
        to_specialist: SpecialistType,
        trigger: str,
        rationale: str,
        carry_over_context: str = "",
    ) -> Dict[str, Any]:
        """Build specialist switch context."""
        return {
            "session_id": session_id,
            "from_specialist": from_specialist,
            "to_specialist": to_specialist,
            "switch_trigger": trigger,
            "carry_over_context": carry_over_context,
            "switch_rationale": rationale,
            "expected_benefit": self._estimate_switch_benefit(from_specialist, to_specialist),
            "timestamp": self._get_timestamp(),
        }
    
    def _estimate_switch_benefit(
        self,
        from_specialist: SpecialistType,
        to_specialist: SpecialistType,
    ) -> str:
        """Estimate benefit of specialist switch."""
        if from_specialist == to_specialist:
            return "No change needed"
        
        benefits = {
            (SpecialistType.CORE, SpecialistType.SECURITY_GUARD): "Enhanced security focus",
            (SpecialistType.CORE, SpecialistType.CRITIC): "Improved code quality assessment",
            (SpecialistType.CORE, SpecialistType.BRAINSTORM): "Enhanced ideation and alternatives exploration",
            (SpecialistType.CORE, SpecialistType.ARCH_TECH): "Better architectural decisions",
            (SpecialistType.CORE, SpecialistType.DEEP_ITERATION): "More thorough analysis",
            (SpecialistType.ANALYST, SpecialistType.SECURITY_GUARD): "Security-focused analysis",
            (SpecialistType.ANALYST, SpecialistType.CRITIC): "Quality-focused evaluation",
            (SpecialistType.ANALYST, SpecialistType.BRAINSTORM): "Structured ideation and option generation",
            (SpecialistType.CODER, SpecialistType.ARCH_TECH): "Architecture-aware implementation",
        }
        
        return benefits.get((from_specialist, to_specialist), "Optimized task handling")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()


# Global builders
_config_builder: SpecialistConfigurationBuilder | None = None
_task_builder: DelegationTaskBuilder | None = None


def get_specialist_config_builder() -> SpecialistConfigurationBuilder:
    """Get the global specialist configuration builder."""
    global _config_builder
    if _config_builder is None:
        _config_builder = SpecialistConfigurationBuilder()
    return _config_builder


def get_delegation_task_builder() -> DelegationTaskBuilder:
    """Get the global delegation task builder."""
    global _task_builder
    if _task_builder is None:
        _task_builder = DelegationTaskBuilder()
    return _task_builder
