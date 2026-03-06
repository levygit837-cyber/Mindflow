"""Sub-personalities for MindFlow agents.

These are specialized variants of core personalities that were previously
implemented as separate agents. Now they're unified under the personality
system with the orchestrator dynamically selecting the appropriate one.
"""

from __future__ import annotations

from typing import Any, Dict, List
from dataclasses import dataclass

from mindflow_backend.agents._base import AgentType, ThinkingLevel, SandboxMode, Priority
from mindflow_backend.schemas.orchestration.personality import PersonalityType, TaskComplexity
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class SubPersonalityConfig:
    """Configuration for a sub-personality."""
    
    name: str
    description: str
    base_personality: PersonalityType
    prompt_segments: List[str]
    tools: List[str]
    thinking_level: ThinkingLevel
    sandbox_mode: SandboxMode
    max_iterations: int
    specializations: List[str]
    trigger_keywords: List[str]
    estimated_efficiency_gain: float
    confidence_boost: float


class SubPersonalityBase:
    """Base class for all sub-personalities."""
    
    def __init__(self, config: SubPersonalityConfig):
        self.config = config
        self._logger = get_logger(f"{__name__}.{config.name.lower()}")
    
    def get_prompt_segments(self) -> List[str]:
        """Get prompt segments for this sub-personality."""
        return self.config.prompt_segments
    
    def get_tools(self) -> List[str]:
        """Get tools for this sub-personality."""
        return self.config.tools
    
    def get_thinking_level(self) -> ThinkingLevel:
        """Get thinking level for this sub-personality."""
        return self.config.thinking_level
    
    def get_sandbox_mode(self) -> SandboxMode:
        """Get sandbox mode for this sub-personality."""
        return self.config.sandbox_mode
    
    def get_max_iterations(self) -> int:
        """Get max iterations for this sub-personality."""
        return self.config.max_iterations
    
    def matches_task(self, task_description: str, context: List[str]) -> float:
        """Calculate match score for this sub-personality."""
        score = 0.0
        task_lower = task_description.lower()
        context_lower = " ".join(context).lower()
        
        # Check trigger keywords
        keyword_matches = sum(
            1 for keyword in self.config.trigger_keywords
            if keyword in task_lower or keyword in context_lower
        )
        if keyword_matches > 0:
            score += 0.3 * keyword_matches
        
        # Check specializations
        spec_matches = sum(
            1 for spec in self.config.specializations
            if spec in task_lower or spec in context_lower
        )
        if spec_matches > 0:
            score += 0.2 * spec_matches
        
        # Add base confidence boost
        score += self.config.confidence_boost
        
        return min(score, 1.0)


class SecurityGuardPersonality(SubPersonalityBase):
    """Security-focused sub-personality for vulnerability analysis and security audits."""
    
    def __init__(self):
        config = SubPersonalityConfig(
            name="security_guard",
            description="Specialized in security analysis, vulnerability detection, and security audits",
            base_personality=PersonalityType.ANALYST,
            prompt_segments=["core", "read", "security"],
            tools=["CODE_ANALYSIS", "FILESYSTEM", "SECURITY_SCAN"],
            thinking_level=ThinkingLevel.HIGH,
            sandbox_mode=SandboxMode.READ_ONLY,
            max_iterations=1,
            specializations=["security", "vulnerability", "audit", "auth", "permission"],
            trigger_keywords=["security", "vulnerability", "audit", "auth", "permission", "secure"],
            estimated_efficiency_gain=0.3,
            confidence_boost=0.2,
        )
        super().__init__(config)


class CriticPersonality(SubPersonalityBase):
    """Critic sub-personality for code review and quality assessment."""
    
    def __init__(self):
        config = SubPersonalityConfig(
            name="critic",
            description="Specialized in code review, quality assessment, and constructive criticism",
            base_personality=PersonalityType.ANALYST,
            prompt_segments=["core", "read", "review"],
            tools=["CODE_ANALYSIS", "QUALITY_METRICS"],
            thinking_level=ThinkingLevel.HIGH,
            sandbox_mode=SandboxMode.NONE,
            max_iterations=1,
            specializations=["review", "critique", "quality", "best_practices"],
            trigger_keywords=["review", "critique", "evaluate", "quality", "improve", "critic"],
            estimated_efficiency_gain=0.25,
            confidence_boost=0.15,
        )
        super().__init__(config)


class CreativePersonality(SubPersonalityBase):
    """Creative sub-personality for brainstorming and alternative solutions."""
    
    def __init__(self):
        config = SubPersonalityConfig(
            name="creative",
            description="Specialized in creative problem-solving and brainstorming alternative approaches",
            base_personality=PersonalityType.ANALYST,
            prompt_segments=["core", "read", "brainstorm"],
            tools=["CODE_ANALYSIS", "BRAINSTORM"],
            thinking_level=ThinkingLevel.HIGH,
            sandbox_mode=SandboxMode.NONE,
            max_iterations=2,
            specializations=["creative", "brainstorm", "alternative", "innovative"],
            trigger_keywords=["brainstorm", "creative", "alternative", "innovate", "explore"],
            estimated_efficiency_gain=0.35,
            confidence_boost=0.25,
        )
        super().__init__(config)


class ArchTechPersonality(SubPersonalityBase):
    """Architecture-focused sub-personality for design and structural decisions."""
    
    def __init__(self):
        config = SubPersonalityConfig(
            name="arch_tech",
            description="Specialized in architecture design, patterns, and structural decisions",
            base_personality=PersonalityType.CODER,
            prompt_segments=["core", "tool_use", "architecture"],
            tools=["FILESYSTEM", "CODE_ANALYSIS", "ARCHITECTURE_TOOLS"],
            thinking_level=ThinkingLevel.HIGH,
            sandbox_mode=SandboxMode.NONE,
            max_iterations=2,
            specializations=["architecture", "design", "structure", "pattern"],
            trigger_keywords=["architecture", "design", "structure", "pattern", "architect"],
            estimated_efficiency_gain=0.4,
            confidence_boost=0.3,
        )
        super().__init__(config)


class BrainstormPersonality(SubPersonalityBase):
    """Brainstorming sub-personality for idea generation and exploration."""
    
    def __init__(self):
        config = SubPersonalityConfig(
            name="brainstorm",
            description="Specialized in idea generation and creative exploration",
            base_personality=PersonalityType.ANALYST,
            prompt_segments=["core", "read", "brainstorm"],
            tools=["IDEA_GENERATION", "BRAINSTORM"],
            thinking_level=ThinkingLevel.HIGH,
            sandbox_mode=SandboxMode.NONE,
            max_iterations=2,
            specializations=["brainstorm", "ideas", "exploration", "possibilities"],
            trigger_keywords=["brainstorm", "ideas", "explore", "possibilities", "generate"],
            estimated_efficiency_gain=0.3,
            confidence_boost=0.2,
        )
        super().__init__(config)


class DeepIterationPersonality(SubPersonalityBase):
    """Deep iteration sub-personality for thorough analysis and refinement."""
    
    def __init__(self):
        config = SubPersonalityConfig(
            name="deep_iteration",
            description="Specialized in deep analysis and iterative refinement",
            base_personality=PersonalityType.ANALYST,
            prompt_segments=["core", "read", "deep"],
            tools=["CODE_ANALYSIS", "FILESYSTEM", "REFACTORING"],
            thinking_level=ThinkingLevel.HIGH,
            sandbox_mode=SandboxMode.NONE,
            max_iterations=3,
            specializations=["deep", "thorough", "iteration", "refine", "analyze"],
            trigger_keywords=["deep", "thorough", "iteration", "refine", "analyze", "detailed"],
            estimated_efficiency_gain=0.35,
            confidence_boost=0.25,
        )
        super().__init__(config)


# Registry of all sub-personalities
SUB_PERSONALITIES: Dict[str, SubPersonalityBase] = {
    "security_guard": SecurityGuardPersonality(),
    "creative": CreativePersonality(),
    "critic": CriticPersonality(),
    "arch_tech": ArchTechPersonality(),
    "brainstorm": BrainstormPersonality(),
    "deep_iteration": DeepIterationPersonality(),
}


def get_sub_personality(name: str) -> SubPersonalityBase | None:
    """Get a sub-personality by name."""
    return SUB_PERSONALITIES.get(name)


def get_all_sub_personalities() -> List[SubPersonalityBase]:
    """Get all available sub-personalities."""
    return list(SUB_PERSONALITIES.values())


def find_best_sub_personality(
    task_description: str,
    context: List[str],
    base_personality: PersonalityType | None = None,
) -> SubPersonalityBase | None:
    """Find the best matching sub-personality for a task."""
    candidates = []
    
    for sub_personality in get_all_sub_personalities():
        # Filter by base personality if specified
        if base_personality and sub_personality.config.base_personality != base_personality:
            continue
        
        match_score = sub_personality.matches_task(task_description, context)
        if match_score > 0.3:  # Minimum threshold
            candidates.append((sub_personality, match_score))
    
    # Sort by match score
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    return candidates[0][0] if candidates else None


def register_sub_personality(name: str, sub_personality: SubPersonalityBase) -> None:
    """Register a new sub-personality."""
    SUB_PERSONALITIES[name] = sub_personality
    _logger.info("sub_personality_registered", name=name)
