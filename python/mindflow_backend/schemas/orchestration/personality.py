"""Personality selection schemas for Orchestrator dynamic personality switching.

Defines contracts for personality selection decisions, switch context,
and personality-specific task configuration.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SpecialistType(StrEnum):
    """Available specialist types for dynamic selection."""
    
    CORE = "core"
    CODER = "coder"
    ANALYST = "analyst"
    SECURITY_GUARD = "security_guard"
    CRITIC = "critic"
    BRAINSTORM = "brainstorm"
    ARCH_TECH = "arch_tech"
    DEEP_ITERATION = "deep_iteration"


class TaskComplexity(StrEnum):
    """Complexity classification for personality selection."""
    
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class SpecializationRequirement(StrEnum):
    """Specialized capabilities required for task."""
    
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "code_review"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    IMPLEMENTATION = "implementation"


class PersonalitySwitchTrigger(StrEnum):
    """What triggered the personality switch."""
    
    TASK_TYPE = "task_type"
    CONTEXT_REQUIREMENT = "context_requirement"
    USER_EXPLICIT = "user_explicit"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    FAILURE_RECOVERY = "failure_recovery"


# ---------------------------------------------------------------------------
# Personality Selection Decision
# ---------------------------------------------------------------------------

class SpecialistSelection(BaseModel):
    """Decision schema for personality selection.
    
    Encapsulates the Orchestrator's reasoning for choosing
    a specific personality for a given task.
    """
    
    task_id: str
    task_complexity: TaskComplexity
    requires_specialization: SpecializationRequirement | None = None
    context_requirements: list[str] = Field(default_factory=list)
    selected_specialist: SpecialistType
    alternative_specialists: list[SpecialistType] = Field(default_factory=list)
    personality_switch_reason: str = Field(
        description="Why this personality was chosen over alternatives."
    )
    confidence_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in this personality selection decision.",
    )
    performance_expectation: str = Field(
        default="",
        description="Expected performance improvement with this personality.",
    )
    estimated_tokens_saved: int = Field(
        default=0,
        ge=0,
        description="Estimated token savings from optimal personality selection.",
    )


# ---------------------------------------------------------------------------
# Personality Switch Context
# ---------------------------------------------------------------------------

class SpecialistSwitchContext(BaseModel):
    """Context for personality switching operations.
    
    Tracks personality transitions and provides continuity
    across personality changes.
    """
    
    session_id: str
    from_personality: SpecialistType
    to_personality: SpecialistType
    switch_trigger: PersonalitySwitchTrigger
    carry_over_context: str = Field(
        default="",
        description="Context to preserve from previous personality.",
    )
    switch_rationale: str = Field(
        description="Detailed reasoning for this personality switch.",
    )
    expected_benefit: str = Field(
        default="",
        description="Expected benefit from this personality change.",
    )
    timestamp: str = Field(
        default="",
        description="When the switch occurred.",
    )


# ---------------------------------------------------------------------------
# Personality Configuration
# ---------------------------------------------------------------------------

class SpecialistConfiguration(BaseModel):
    """Configuration for a specific personality.
    
    Defines how a personality should be configured for a given task.
    """
    
    personality: SpecialistType
    agent_type: str  # ANALYST, CODER, etc.
    prompt_segments: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    thinking_level: str = "MEDIUM"
    sandbox_mode: str = "NONE"
    priority_modifier: int = Field(default=0, ge=-2, le=2)
    context_strategy: Literal["maintain", "fresh", "carry_summary"] = "maintain"
    max_iterations: int = Field(default=1, ge=1, le=10)


# ---------------------------------------------------------------------------
# Personality Decision Result
# ---------------------------------------------------------------------------

class SpecialistDecisionResult(BaseModel):
    """Result of personality selection and configuration.
    
    Complete package that the Orchestrator uses to delegate
    a task with the optimal personality configuration.
    """
    
    selection: SpecialistSelection
    configuration: SpecialistConfiguration
    delegation_task: dict = Field(
        description="Delegation task configured for selected personality.",
    )
    estimated_efficiency_gain: float = Field(
        default=0.0,
        description="Estimated efficiency gain from personality selection.",
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback to default personality was used.",
    )


# ---------------------------------------------------------------------------
# Personality Selection Rules
# ---------------------------------------------------------------------------

class SpecialistSelectionRule(BaseModel):
    """Rule for personality selection decisions.
    
    Configurable heuristics that guide personality selection.
    """
    
    name: str
    condition_task_types: list[str] = Field(default_factory=list)
    condition_keywords: list[str] = Field(default_factory=list)
    condition_complexity: list[TaskComplexity] = Field(default_factory=list)
    required_specialization: SpecializationRequirement | None = None
    target_personality: SpecialistType
    priority: int = Field(default=1, ge=1, le=10)
    confidence_boost: float = Field(default=0.0, ge=0.0, le=1.0)
    description: str = ""


# ---------------------------------------------------------------------------
# Personality Cache Entry
# ---------------------------------------------------------------------------

class SpecialistCacheEntry(BaseModel):
    """Cached personality decision for performance optimization."""
    
    task_signature: str = Field(
        description="Hash of task characteristics for cache lookup.",
    )
    personality: SpecialistType
    confidence: float = 0.8
    usage_count: int = Field(default=0, ge=0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    last_used: str = Field(default="")
    estimated_tokens_saved: int = Field(default=0, ge=0)
