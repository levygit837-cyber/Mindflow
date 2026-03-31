"""Specialist selection schemas for Orchestrator dynamic specialist switching.

Defines contracts for specialist selection decisions, switch context,
and specialist-specific task configuration.
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
    """Complexity classification for specialist selection."""
    
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class SpecializationRequirement(StrEnum):
    """Specialized capabilities required for task."""
    
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "code_review"
    BRAINSTORM = "brainstorm"
    ANALYSIS = "analysis"
    IMPLEMENTATION = "implementation"


class SpecialistSwitchTrigger(StrEnum):
    """What triggered the specialist switch."""
    
    TASK_TYPE = "task_type"
    CONTEXT_REQUIREMENT = "context_requirement"
    USER_EXPLICIT = "user_explicit"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    FAILURE_RECOVERY = "failure_recovery"


# ---------------------------------------------------------------------------
# Specialist Selection Decision
# ---------------------------------------------------------------------------

class SpecialistSelection(BaseModel):
    """Decision schema for specialist selection.
    
    Encapsulates the Orchestrator's reasoning for choosing
    a specific specialist for a given task.
    """
    
    task_id: str
    task_complexity: TaskComplexity
    requires_specialization: SpecializationRequirement | None = None
    context_requirements: list[str] = Field(default_factory=list)
    selected_specialist: SpecialistType
    alternative_specialists: list[SpecialistType] = Field(default_factory=list)
    specialist_switch_reason: str = Field(
        description="Why this specialist was chosen over alternatives."
    )
    confidence_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in this specialist selection decision.",
    )
    performance_expectation: str = Field(
        default="",
        description="Expected performance improvement with this specialist.",
    )
    estimated_tokens_saved: int = Field(
        default=0,
        ge=0,
        description="Estimated token savings from optimal specialist selection.",
    )


# ---------------------------------------------------------------------------
# Specialist Switch Context
# ---------------------------------------------------------------------------

class SpecialistSwitchContext(BaseModel):
    """Context for specialist switching operations.
    
    Tracks specialist transitions and provides continuity
    across specialist changes.
    """
    
    session_id: str
    from_specialist: SpecialistType
    to_specialist: SpecialistType
    switch_trigger: SpecialistSwitchTrigger
    carry_over_context: str = Field(
        default="",
        description="Context to preserve from previous specialist.",
    )
    switch_rationale: str = Field(
        description="Detailed reasoning for this specialist switch.",
    )
    expected_benefit: str = Field(
        default="",
        description="Expected benefit from this specialist change.",
    )
    timestamp: str = Field(
        default="",
        description="When the switch occurred.",
    )


# ---------------------------------------------------------------------------
# Specialist Configuration
# ---------------------------------------------------------------------------

class SpecialistConfiguration(BaseModel):
    """Configuration for a specific specialist.
    
    Defines how a specialist should be configured for a given task.
    """
    
    specialist: SpecialistType
    agent_type: str  # ANALYST, CODER, etc.
    prompt_segments: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    thinking_level: str = "MEDIUM"
    sandbox_mode: str = "NONE"
    priority_modifier: int = Field(default=0, ge=-2, le=2)
    context_strategy: Literal["maintain", "fresh", "carry_summary"] = "maintain"
    max_iterations: int = Field(default=1, ge=1, le=10)


# ---------------------------------------------------------------------------
# Specialist Decision Result
# ---------------------------------------------------------------------------

class SpecialistDecisionResult(BaseModel):
    """Result of specialist selection and configuration.
    
    Complete package that the Orchestrator uses to delegate
    a task with the optimal specialist configuration.
    """
    
    selection: SpecialistSelection
    configuration: SpecialistConfiguration
    delegation_task: dict = Field(
        description="Delegation task configured for selected specialist.",
    )
    estimated_efficiency_gain: float = Field(
        default=0.0,
        description="Estimated efficiency gain from specialist selection.",
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback to default specialist was used.",
    )


# ---------------------------------------------------------------------------
# Specialist Selection Rules
# ---------------------------------------------------------------------------

class SpecialistSelectionRule(BaseModel):
    """Rule for specialist selection decisions.
    
    Configurable heuristics that guide specialist selection.
    """
    
    name: str
    condition_task_types: list[str] = Field(default_factory=list)
    condition_keywords: list[str] = Field(default_factory=list)
    condition_complexity: list[TaskComplexity] = Field(default_factory=list)
    required_specialization: SpecializationRequirement | None = None
    target_specialist: SpecialistType
    priority: int = Field(default=1, ge=1, le=10)
    confidence_boost: float = Field(default=0.0, ge=0.0, le=1.0)
    description: str = ""


# ---------------------------------------------------------------------------
# Specialist Cache Entry
# ---------------------------------------------------------------------------

class SpecialistCacheEntry(BaseModel):
    """Cached specialist decision for performance optimization."""
    
    task_signature: str = Field(
        description="Hash of task characteristics for cache lookup.",
    )
    specialist: SpecialistType
    confidence: float = 0.8
    usage_count: int = Field(default=0, ge=0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    last_used: str = Field(default="")
    estimated_tokens_saved: int = Field(default=0, ge=0)
