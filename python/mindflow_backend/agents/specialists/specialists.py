"""Specialists for MindFlow agents.

These are specialized variants of core specialists that were previously
implemented as separate agents. Now they're unified under the specialist
system with the orchestrator dynamically selecting the appropriate one.
"""

from __future__ import annotations

from typing import Any, Dict, List
from dataclasses import dataclass

from mindflow_backend.agents._base import AgentType, ThinkingLevel, SandboxMode, Priority
from mindflow_backend.schemas.orchestration.specialists import SpecialistType, TaskComplexity
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class SpecialistConfig:
    """Configuration for a specialist."""
    
    name: str
    description: str
    base_specialist: SpecialistType
    prompt_segments: List[str]
    tools: List[str]
    thinking_level: ThinkingLevel
    sandbox_mode: SandboxMode
    max_iterations: int
    specializations: List[str]
    trigger_keywords: List[str]
    estimated_efficiency_gain: float
    confidence_boost: float


class SpecialistBase:
    """Base class for all specialists."""
    
    def __init__(self, config: SpecialistConfig):
        self.config = config
        self._logger = get_logger(f"{__name__}.{config.name.lower()}")
    
    def get_prompt_segments(self) -> List[str]:
        """Get prompt segments for this specialist."""
        return self.config.prompt_segments
    
    def get_tools(self) -> List[str]:
        """Get tools for this specialist."""
        return self.config.tools
    
    def get_thinking_level(self) -> ThinkingLevel:
        """Get thinking level for this specialist."""
        return self.config.thinking_level
    
    def get_sandbox_mode(self) -> SandboxMode:
        """Get sandbox mode for this specialist."""
        return self.config.sandbox_mode
    
    def get_max_iterations(self) -> int:
        """Get max iterations for this specialist."""
        return self.config.max_iterations
    
    def matches_task(self, task_description: str, context: List[str]) -> float:
        """Calculate match score for this specialist."""
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


class SecuritySpecialist(SpecialistBase):
    """Security-focused specialist for vulnerability analysis and security audits."""
    
    def __init__(self):
        config = SpecialistConfig(
            name="security_guard",
            description="Specialized in security analysis, vulnerability detection, and security audits",
            base_specialist=SpecialistType.ANALYST,
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


class ReviewSpecialist(SpecialistBase):
    """Review specialist for code review and quality assessment."""
    
    def __init__(self):
        config = SpecialistConfig(
            name="critic",
            description="Specialized in code review, quality assessment, and constructive criticism",
            base_specialist=SpecialistType.ANALYST,
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


class CreativeSpecialist(SpecialistBase):
    """Creative specialist for brainstorming and alternative solutions."""
    
    def __init__(self):
        config = SpecialistConfig(
            name="creative",
            description="Specialized in creative problem-solving and brainstorming alternative approaches",
            base_specialist=SpecialistType.ANALYST,
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


class ArchitectureSpecialist(SpecialistBase):
    """Architecture-focused specialist for design and structural decisions."""
    
    def __init__(self):
        config = SpecialistConfig(
            name="arch_tech",
            description="Specialized in architecture design, patterns, and structural decisions",
            base_specialist=SpecialistType.CODER,
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


class BrainstormSpecialist(SpecialistBase):
    """Brainstorming specialist for idea generation and exploration."""
    
    def __init__(self):
        config = SpecialistConfig(
            name="brainstorm",
            description="Specialized in idea generation and creative exploration",
            base_specialist=SpecialistType.ANALYST,
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


class DeepAnalysisSpecialist(SpecialistBase):
    """Deep analysis specialist for thorough analysis and refinement."""
    
    def __init__(self):
        config = SpecialistConfig(
            name="deep_iteration",
            description="Specialized in deep analysis and iterative refinement",
            base_specialist=SpecialistType.ANALYST,
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


# Registry of all specialists
SPECIALISTS: Dict[str, SpecialistBase] = {
    "security_guard": SecuritySpecialist(),
    "creative": CreativeSpecialist(),
    "critic": ReviewSpecialist(),
    "arch_tech": ArchitectureSpecialist(),
    "brainstorm": BrainstormSpecialist(),
    "deep_iteration": DeepAnalysisSpecialist(),
}


def get_specialist(name: str) -> SpecialistBase | None:
    """Get a specialist by name."""
    return SPECIALISTS.get(name)


def get_all_specialists() -> List[SpecialistBase]:
    """Get all available specialists."""
    return list(SPECIALISTS.values())


def find_best_specialist(
    task_description: str,
    context: List[str],
    base_specialist: SpecialistType | None = None,
) -> SpecialistBase | None:
    """Find the best matching specialist for a task."""
    candidates = []
    
    for specialist in get_all_specialists():
        # Filter by base specialist if specified
        if base_specialist and specialist.config.base_specialist != base_specialist:
            continue
        
        match_score = specialist.matches_task(task_description, context)
        if match_score > 0.3:  # Minimum threshold
            candidates.append((specialist, match_score))
    
    # Sort by match score
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    return candidates[0][0] if candidates else None


def register_specialist(name: str, specialist: SpecialistBase) -> None:
    """Register a new specialist."""
    SPECIALISTS[name] = specialist
    _logger.info("specialist_registered", name=name)
