"""Common types and configurations for graphs."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GraphType(StrEnum):
    """Types of graphs supported by the system."""
    
    # Orchestrator
    SIMPLE = "simple"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    CYCLIC = "cyclic"
    DECOMPOSITION = "decomposition"
    
    # Analysis (Fase 2A)
    ANALYSIS = "analysis"
    DEEP_INVESTIGATION = "deep_investigation"
    SECURITY_AUDIT = "security_audit"
    CODE_REVIEW = "code_review"
    
    # Coding (Fase 2A)
    CODING_TASK = "coding_task"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    
    # Research (Fase 2A)
    WEB_RESEARCH = "web_research"
    COMPARISON = "comparison"


class NodeConnection(BaseModel):
    """Represents a connection between nodes in a graph."""
    
    source_node: str
    target_node: str
    condition: str | None = None  # Optional condition for conditional edges
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class GraphConfig(BaseModel):
    """Configuration for graph execution."""
    
    graph_type: GraphType = GraphType.SIMPLE
    max_execution_time: float | None = Field(default=None, gt=0.0)
    enable_streaming: bool = True
    enable_state_persistence: bool = False
    retry_attempts: int = Field(default=3, ge=0)
    timeout_per_node: float | None = Field(default=30.0, gt=0.0)
    custom_parameters: dict[str, Any] = Field(default_factory=dict)


class GraphMetrics(BaseModel):
    """Metrics collected during graph execution."""
    
    execution_time: float
    nodes_executed: int
    nodes_failed: int
    total_tokens_used: int
    memory_usage: dict[str, Any] | None = None
    error_details: list[str] = Field(default_factory=list)
