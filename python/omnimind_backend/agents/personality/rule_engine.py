"""Rule engine for personality selection.

Implements rule evaluation and candidate selection
for dynamic personality switching.
"""

from __future__ import annotations

from typing import Any, Dict, List
from dataclasses import dataclass

from omnimind_backend.agents.core.interfaces import RuleEngine
from omnimind_backend.agents.core.exceptions import RuleEngineError
from omnimind_backend.schemas.orchestration.personality import PersonalityType, TaskComplexity, SpecializationRequirement
from omnimind_backend.config.personality_rules import get_personality_rules, RuleConfig
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class PersonalityCandidate:
    """Represents a personality candidate with evaluation metrics."""
    
    personality: PersonalityType
    rule_name: str
    confidence: float
    reason: str
    estimated_tokens_saved: int
    estimated_efficiency_gain: float
    priority: int


class PersonalityRuleEngine(RuleEngine):
    """Evaluates personality selection rules and generates candidates."""
    
    def __init__(self, rules_config: RuleConfig | None = None):
        self.rules_config = rules_config or get_personality_rules()
        self.custom_rules: List[RuleConfig] = []
    
    def evaluate(
        self,
        task_description: str,
        task_complexity: TaskComplexity,
        specialization: SpecializationRequirement | None,
    ) -> List[PersonalityCandidate]:
        """Evaluate rules and return personality candidates."""
        try:
            _logger.debug(
                "rule_evaluation_started",
                complexity=task_complexity,
                specialization=specialization,
                rules_count=len(self.rules_config.get_all_rules()) + len(self.custom_rules)
            )
            
            candidates = []
            description_lower = task_description.lower()
            
            # Evaluate default rules
            for rule in self.rules_config.get_all_rules():
                candidate = self._evaluate_rule(
                    rule, description_lower, task_complexity, specialization
                )
                if candidate:
                    candidates.append(candidate)
            
            # Evaluate custom rules
            for rule in self.custom_rules:
                candidate = self._evaluate_rule(
                    rule, description_lower, task_complexity, specialization
                )
                if candidate:
                    candidates.append(candidate)
            
            # Sort candidates by priority and confidence
            candidates.sort(
                key=lambda c: (c.priority, -c.confidence),
                reverse=True
            )
            
            _logger.debug(
                "rule_evaluation_completed",
                candidates_count=len(candidates),
                top_candidate=candidates[0].personality if candidates else None
            )
            
            return candidates
        
        except Exception as e:
            _logger.error("rule_evaluation_failed", error=str(e))
            raise RuleEngineError(
                f"Rule evaluation failed: {e}",
                rule_name="evaluation"
            )
    
    def add_rule(self, rule: Dict[str, Any]) -> None:
        """Add new rule to engine."""
        try:
            rule_config = RuleConfig(
                name=rule["name"],
                target_personality=PersonalityType(rule["target_personality"]),
                priority=rule.get("priority", 10),
                confidence_boost=rule.get("confidence_boost", 0.0),
                description=rule.get("description", ""),
                condition_task_types=rule.get("condition_task_types", []),
                condition_keywords=rule.get("condition_keywords", []),
                condition_complexity=[
                    TaskComplexity(c) for c in rule.get("condition_complexity", [])
                ],
                required_specialization=(
                    SpecializationRequirement(rule["required_specialization"])
                    if "required_specialization" in rule
                    else None
                ),
                estimated_tokens_saved=rule.get("estimated_tokens_saved", 100),
                estimated_efficiency_gain=rule.get("estimated_efficiency_gain", 0.1),
            )
            
            self.custom_rules.append(rule_config)
            _logger.info("custom_rule_added", rule_name=rule_config.name)
        
        except Exception as e:
            _logger.error("rule_addition_failed", rule=rule, error=str(e))
            raise RuleEngineError(
                f"Failed to add rule: {e}",
                rule_name=rule.get("name", "unknown")
            )
    
    def _evaluate_rule(
        self,
        rule: RuleConfig,
        description_lower: str,
        task_complexity: TaskComplexity,
        specialization: SpecializationRequirement | None,
    ) -> PersonalityCandidate | None:
        """Evaluate a single rule and return candidate if it matches."""
        score = 0.0
        
        # Check task type matches
        if rule.condition_task_types:
            task_type_matches = sum(
                1 for task_type in rule.condition_task_types
                if task_type in description_lower
            )
            if task_type_matches > 0:
                score += 2.0 * task_type_matches
        
        # Check keyword matches
        if rule.condition_keywords:
            keyword_matches = sum(
                1 for keyword in rule.condition_keywords
                if keyword in description_lower
            )
            if keyword_matches > 0:
                score += 0.5 * keyword_matches
        
        # Check complexity matches
        if rule.condition_complexity and task_complexity in rule.condition_complexity:
            score += 1.5
        
        # Check specialization matches
        if (
            rule.required_specialization and
            rule.required_specialization == specialization
        ):
            score += 2.5
        
        # If rule matches, create candidate
        if score > 0:
            confidence = min(0.5 + rule.confidence_boost + (score / 10), 1.0)
            
            return PersonalityCandidate(
                personality=rule.target_personality,
                rule_name=rule.name,
                confidence=confidence,
                reason=self._generate_reason(rule, score, description_lower),
                estimated_tokens_saved=rule.estimated_tokens_saved,
                estimated_efficiency_gain=rule.estimated_efficiency_gain,
                priority=rule.priority,
            )
        
        return None
    
    def _generate_reason(
        self,
        rule: RuleConfig,
        score: float,
        description_lower: str,
    ) -> str:
        """Generate reason for rule match."""
        reasons = []
        
        # Task type matches
        task_type_matches = [
            task_type for task_type in rule.condition_task_types
            if task_type in description_lower
        ]
        if task_type_matches:
            reasons.append(f"matches task types: {', '.join(task_type_matches)}")
        
        # Keyword matches
        keyword_matches = [
            keyword for keyword in rule.condition_keywords
            if keyword in description_lower
        ]
        if keyword_matches:
            reasons.append(f"matches keywords: {', '.join(keyword_matches)}")
        
        # Complexity match
        if rule.condition_complexity:
            reasons.append(f"matches complexity requirement")
        
        # Specialization match
        if rule.required_specialization:
            reasons.append(f"matches specialization: {rule.required_specialization}")
        
        return rule.description + " (" + "; ".join(reasons) + ")"
    
    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded rules."""
        default_rules = self.rules_config.get_all_rules()
        all_rules = default_rules + self.custom_rules
        
        # Count by personality
        personality_counts = {}
        for rule in all_rules:
            personality = rule.target_personality
            personality_counts[personality] = personality_counts.get(personality, 0) + 1
        
        # Count by priority
        priority_counts = {}
        for rule in all_rules:
            priority = rule.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            "total_rules": len(all_rules),
            "default_rules": len(default_rules),
            "custom_rules": len(self.custom_rules),
            "personalities": personality_counts,
            "priorities": priority_counts,
            "rules_by_priority": {
                rule.name: rule.priority for rule in all_rules
            },
        }


# Global rule engine instance
_rule_engine: PersonalityRuleEngine | None = None


def get_personality_rule_engine() -> PersonalityRuleEngine:
    """Get the global personality rule engine instance."""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = PersonalityRuleEngine()
    return _rule_engine
