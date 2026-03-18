"""Specialist rule configuration.

Centralized configuration for specialist selection rules
and their associated parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from mindflow_backend.schemas.orchestration.specialists import SpecialistType, TaskComplexity, SpecializationRequirement


@dataclass
class RuleConfig:
    """Configuration for a single specialist selection rule."""
    
    name: str
    target_specialist: SpecialistType
    priority: int
    confidence_boost: float
    description: str
    
    # Conditions
    condition_task_types: List[str]
    condition_keywords: List[str]
    condition_complexity: List[TaskComplexity]
    required_specialization: Optional[SpecializationRequirement]
    
    # Performance
    estimated_tokens_saved: int = 100
    estimated_efficiency_gain: float = 0.1


@dataclass
class SpecialistRuleConfig:
    """Complete configuration for specialist selection rules."""
    
    # Default rules
    security_audit: RuleConfig
    architecture_design: RuleConfig
    code_review: RuleConfig
    brainstorm: RuleConfig
    deep_analysis: RuleConfig
    
    # Rule evaluation
    max_rules_per_task: int = 10
    min_confidence_score: float = 0.5
    enable_rule_caching: bool = True
    
    # Specialist switching
    switch_cost_threshold: float = 0.15
    max_switches_per_session: int = 5
    switch_cooldown_minutes: int = 2
    
    def get_all_rules(self) -> List[RuleConfig]:
        """Get all configured rules."""
        return [
            self.security_audit,
            self.architecture_design,
            self.code_review,
            self.brainstorm,
            self.deep_analysis,
        ]
    
    def get_rules_by_priority(self) -> List[RuleConfig]:
        """Get rules sorted by priority."""
        return sorted(self.get_all_rules(), key=lambda r: r.priority)


def create_default_rules() -> SpecialistRuleConfig:
    """Create default specialist rule configuration."""
    return SpecialistRuleConfig(
        security_audit=RuleConfig(
            name="security_audit",
            target_specialist=SpecialistType.SECURITY_GUARD,
            priority=1,
            confidence_boost=0.3,
            description="Security-related tasks use SecurityGuard specialist",
            condition_task_types=["audit", "security", "vulnerability", "scan"],
            condition_keywords=["security", "vulnerability", "audit", "scan", "auth"],
            condition_complexity=[],
            required_specialization=SpecializationRequirement.SECURITY,
            estimated_tokens_saved=200,
            estimated_efficiency_gain=0.25,
        ),
        
        architecture_design=RuleConfig(
            name="architecture_design",
            target_specialist=SpecialistType.ARCH_TECH,
            priority=2,
            confidence_boost=0.2,
            description="Architecture tasks use ArchTech specialist",
            condition_task_types=["architecture", "design", "structure"],
            condition_keywords=["architecture", "design", "structure", "pattern", "system"],
            condition_complexity=[],
            required_specialization=SpecializationRequirement.ARCHITECTURE,
            estimated_tokens_saved=250,
            estimated_efficiency_gain=0.2,
        ),
        
        code_review=RuleConfig(
            name="code_review",
            target_specialist=SpecialistType.CRITIC,
            priority=2,
            confidence_boost=0.2,
            description="Code review tasks use Critic specialist",
            condition_task_types=["review", "critique", "evaluate"],
            condition_keywords=["review", "critique", "evaluate", "quality", "best practice"],
            condition_complexity=[],
            required_specialization=SpecializationRequirement.CODE_REVIEW,
            estimated_tokens_saved=150,
            estimated_efficiency_gain=0.15,
        ),

        brainstorm=RuleConfig(
            name="brainstorm",
            target_specialist=SpecialistType.BRAINSTORM,
            priority=2,
            confidence_boost=0.2,
            description="Ideation and alternatives exploration use Brainstorm specialist",
            condition_task_types=["brainstorm", "ideate", "explore", "alternative"],
            condition_keywords=["brainstorm", "creative", "alternative", "explore", "ideas", "ideation"],
            condition_complexity=[],
            required_specialization=SpecializationRequirement.BRAINSTORM,
            estimated_tokens_saved=120,
            estimated_efficiency_gain=0.12,
        ),
        
        deep_analysis=RuleConfig(
            name="deep_analysis",
            target_specialist=SpecialistType.DEEP_ITERATION,
            priority=2,
            confidence_boost=0.25,
            description="Complex analysis tasks use DeepIteration specialist",
            condition_task_types=[],
            condition_keywords=["deep", "comprehensive", "thorough", "end-to-end"],
            condition_complexity=[TaskComplexity.COMPLEX],
            required_specialization=SpecializationRequirement.ANALYSIS,
            estimated_tokens_saved=400,
            estimated_efficiency_gain=0.35,
        ),
    )


# Global configuration instance
_rule_config: Optional[SpecialistRuleConfig] = None


def get_specialist_rules() -> SpecialistRuleConfig:
    """Get the global specialist rule configuration."""
    global _rule_config
    if _rule_config is None:
        _rule_config = create_default_rules()
    return _rule_config


def set_specialist_rules(config: SpecialistRuleConfig) -> None:
    """Set the global specialist rule configuration."""
    global _rule_config
    _rule_config = config


def add_custom_rule(rule: RuleConfig) -> None:
    """Add a custom rule to the configuration."""
    config = get_specialist_rules()
    # Add as a dynamic attribute
    setattr(config, rule.name, rule)
