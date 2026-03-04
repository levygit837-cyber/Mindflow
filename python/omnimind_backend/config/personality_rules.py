"""Personality rule configuration.

Centralized configuration for personality selection rules
and their associated parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from omnimind_backend.schemas.orchestration.personality import PersonalityType, TaskComplexity, SpecializationRequirement


@dataclass
class RuleConfig:
    """Configuration for a single personality selection rule."""
    
    name: str
    target_personality: PersonalityType
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
class PersonalityRuleConfig:
    """Complete configuration for personality selection rules."""
    
    # Default rules
    security_audit: RuleConfig
    architecture_design: RuleConfig
    code_review: RuleConfig
    creative_exploration: RuleConfig
    deep_analysis: RuleConfig
    
    # Rule evaluation
    max_rules_per_task: int = 10
    min_confidence_score: float = 0.5
    enable_rule_caching: bool = True
    
    # Personality switching
    switch_cost_threshold: float = 0.15
    max_switches_per_session: int = 5
    switch_cooldown_minutes: int = 2
    
    def get_all_rules(self) -> List[RuleConfig]:
        """Get all configured rules."""
        return [
            self.security_audit,
            self.architecture_design,
            self.code_review,
            self.creative_exploration,
            self.deep_analysis,
        ]
    
    def get_rules_by_priority(self) -> List[RuleConfig]:
        """Get rules sorted by priority."""
        return sorted(self.get_all_rules(), key=lambda r: r.priority)


def create_default_rules() -> PersonalityRuleConfig:
    """Create default personality rule configuration."""
    return PersonalityRuleConfig(
        security_audit=RuleConfig(
            name="security_audit",
            target_personality=PersonalityType.SECURITY_GUARD,
            priority=1,
            confidence_boost=0.3,
            description="Security-related tasks use SecurityGuard personality",
            condition_task_types=["audit", "security", "vulnerability", "scan"],
            condition_keywords=["security", "vulnerability", "audit", "scan", "auth"],
            condition_complexity=[],
            required_specialization=SpecializationRequirement.SECURITY,
            estimated_tokens_saved=200,
            estimated_efficiency_gain=0.25,
        ),
        
        architecture_design=RuleConfig(
            name="architecture_design",
            target_personality=PersonalityType.ARCH_TECH,
            priority=2,
            confidence_boost=0.2,
            description="Architecture tasks use ArchTech personality",
            condition_task_types=["architecture", "design", "structure"],
            condition_keywords=["architecture", "design", "structure", "pattern", "system"],
            condition_complexity=[],
            required_specialization=SpecializationRequirement.ARCHITECTURE,
            estimated_tokens_saved=250,
            estimated_efficiency_gain=0.2,
        ),
        
        code_review=RuleConfig(
            name="code_review",
            target_personality=PersonalityType.CRITIC,
            priority=2,
            confidence_boost=0.2,
            description="Code review tasks use Critic personality",
            condition_task_types=["review", "critique", "evaluate"],
            condition_keywords=["review", "critique", "evaluate", "quality", "best practice"],
            condition_complexity=[],
            required_specialization=SpecializationRequirement.CODE_REVIEW,
            estimated_tokens_saved=150,
            estimated_efficiency_gain=0.15,
        ),
        
        creative_exploration=RuleConfig(
            name="creative_exploration",
            target_personality=PersonalityType.BRAINSTORM,
            priority=3,
            confidence_boost=0.15,
            description="Creative tasks use Brainstorm personality",
            condition_task_types=["brainstorm", "explore", "design", "ideate"],
            condition_keywords=["brainstorm", "explore", "creative", "alternative", "ideate"],
            condition_complexity=[],
            required_specialization=SpecializationRequirement.CREATIVE,
            estimated_tokens_saved=300,
            estimated_efficiency_gain=0.3,
        ),
        
        deep_analysis=RuleConfig(
            name="deep_analysis",
            target_personality=PersonalityType.DEEP_ITERATION,
            priority=2,
            confidence_boost=0.25,
            description="Complex analysis tasks use DeepIteration personality",
            condition_task_types=[],
            condition_keywords=["deep", "comprehensive", "thorough", "end-to-end"],
            condition_complexity=[TaskComplexity.COMPLEX],
            required_specialization=SpecializationRequirement.ANALYSIS,
            estimated_tokens_saved=400,
            estimated_efficiency_gain=0.35,
        ),
    )


# Global configuration instance
_rule_config: Optional[PersonalityRuleConfig] = None


def get_personality_rules() -> PersonalityRuleConfig:
    """Get the global personality rule configuration."""
    global _rule_config
    if _rule_config is None:
        _rule_config = create_default_rules()
    return _rule_config


def set_personality_rules(config: PersonalityRuleConfig) -> None:
    """Set the global personality rule configuration."""
    global _rule_config
    _rule_config = config


def add_custom_rule(rule: RuleConfig) -> None:
    """Add a custom rule to the configuration."""
    config = get_personality_rules()
    # Add as a dynamic attribute
    setattr(config, rule.name, rule)
