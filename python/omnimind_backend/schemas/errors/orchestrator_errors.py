"""Orchestrator-specific error schemas.

Specialized error schemas for routing, decomposition, scheduling,
and dependency management failures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from pydantic import Field

from .base import ErrorSchema, ErrorContext, ErrorSeverity


class OrchestratorErrorSchema(ErrorSchema):
    """Base schema for orchestrator-related errors."""
    
    # Orchestrator information
    orchestrator_version: Optional[str] = Field(default=None, description="Orchestrator version")
    workflow_id: Optional[str] = Field(default=None, description="Workflow ID")
    session_id: Optional[str] = Field(default=None, description="User session ID")
    
    # Execution context
    execution_phase: Optional[str] = Field(
        default=None, 
        description="Phase of orchestrator execution"
    )
    
    class Config:
        extra = "allow"


class RoutingErrorSchema(OrchestratorErrorSchema):
    """Schema for routing and intent analysis failures."""
    
    # Routing details
    routing_method: Optional[str] = Field(default=None, description="Method used for routing")
    message_type: Optional[str] = Field(default=None, description="Type of message being routed")
    
    # Intent analysis
    intent_confidence: Optional[float] = Field(
        default=None, 
        description="Confidence score of intent analysis"
    )
    analyzed_intent: Optional[str] = Field(default=None, description="Intent that was analyzed")
    
    # Agent selection
    candidate_agents: List[str] = Field(
        default_factory=list, 
        description="Agents that were considered"
    )
    selection_conflicts: List[str] = Field(
        default_factory=list, 
        description="Conflicts in agent selection"
    )
    
    # Failure reasons
    routing_failure_reason: Optional[str] = Field(
        default=None, 
        description="Specific reason for routing failure"
    )
    ambiguity_detected: bool = Field(
        default=False, 
        description="Whether routing failed due to ambiguity"
    )


class DecompositionErrorSchema(OrchestratorErrorSchema):
    """Schema for task decomposition failures."""
    
    # Task information
    task_description: Optional[str] = Field(
        default=None, 
        description="Description of task being decomposed"
    )
    task_complexity: Optional[str] = Field(
        default=None, 
        description="Assessed complexity of task"
    )
    
    # Decomposition details
    decomposition_method: Optional[str] = Field(
        default=None, 
        description="Method used for decomposition"
    )
    subtasks_attempted: int = Field(default=0, description="Number of subtasks attempted")
    subtasks_created: int = Field(default=0, description="Number of subtasks successfully created")
    
    # LLM information
    model_used: Optional[str] = Field(default=None, description="Model used for decomposition")
    prompt_tokens: Optional[int] = Field(default=None, description="Tokens used in decomposition prompt")
    
    # Failure details
    decomposition_failure_reason: Optional[str] = Field(
        default=None, 
        description="Reason decomposition failed"
    )
    parsing_error: bool = Field(default=False, description="Whether parsing of LLM response failed")
    validation_failed: bool = Field(default=False, description="Whether validation of subtasks failed")


class SchedulingErrorSchema(OrchestratorErrorSchema):
    """Schema for task scheduling failures."""
    
    # Scheduling details
    scheduling_algorithm: Optional[str] = Field(
        default=None, 
        description="Algorithm used for scheduling"
    )
    total_tasks: int = Field(description="Total number of tasks to schedule")
    scheduled_tasks: int = Field(default=0, description="Number of tasks successfully scheduled")
    
    # Dependency information
    dependency_count: int = Field(default=0, description="Number of dependencies")
    circular_dependencies: List[str] = Field(
        default_factory=list, 
        description="Circular dependencies detected"
    )
    
    # Failure details
    scheduling_failure_reason: Optional[str] = Field(
        default=None, 
        description="Reason scheduling failed"
    )
    cycle_detected: bool = Field(default=False, description="Whether dependency cycle was detected")
    orphaned_tasks: List[str] = Field(
        default_factory=list, 
        description="Tasks that couldn't be scheduled"
    )


class DependencyErrorSchema(OrchestratorErrorSchema):
    """Schema for dependency resolution failures."""
    
    # Dependency details
    dependency_type: Optional[str] = Field(
        default=None, 
        description="Type of dependency (data, execution, etc.)"
    )
    dependent_task: Optional[str] = Field(default=None, description="Task that has dependency")
    required_task: Optional[str] = Field(default=None, description="Task that is required")
    
    # Resolution information
    resolution_method: Optional[str] = Field(
        default=None, 
        description="Method used for dependency resolution"
    )
    resolution_timeout: Optional[float] = Field(
        default=None, 
        description="Timeout for dependency resolution"
    )
    
    # Failure details
    dependency_failure_reason: Optional[str] = Field(
        default=None, 
        description="Reason dependency resolution failed"
    )
    missing_dependencies: List[str] = Field(
        default_factory=list, 
        description="Dependencies that couldn't be resolved"
    )
    circular_reference: bool = Field(
        default=False, 
        description="Whether circular reference was detected"
    )


class GraphExecutionErrorSchema(OrchestratorErrorSchema):
    """Schema for graph execution failures."""
    
    # Graph information
    graph_type: Optional[str] = Field(default=None, description="Type of graph being executed")
    node_count: int = Field(default=0, description="Number of nodes in graph")
    edge_count: int = Field(default=0, description="Number of edges in graph")
    
    # Execution details
    execution_strategy: Optional[str] = Field(
        default=None, 
        description="Strategy used for graph execution"
    )
    completed_nodes: int = Field(default=0, description="Number of completed nodes")
    failed_nodes: List[str] = Field(
        default_factory=list, 
        description="Nodes that failed execution"
    )
    
    # Failure information
    execution_failure_reason: Optional[str] = Field(
        default=None, 
        description="Reason graph execution failed"
    )
    node_failure: Optional[str] = Field(default=None, description="Specific node that caused failure")
    deadlock_detected: bool = Field(default=False, description="Whether deadlock was detected")


class DelegationErrorSchema(OrchestratorErrorSchema):
    """Schema for agent delegation failures."""
    
    # Delegation details
    delegation_type: Optional[str] = Field(default=None, description="Type of delegation")
    source_agent: Optional[str] = Field(default=None, description="Agent making delegation")
    target_agent: Optional[str] = Field(default=None, description="Agent being delegated to")
    
    # Task information
    delegated_task: Optional[str] = Field(default=None, description="Task being delegated")
    task_context: Optional[str] = Field(default=None, description="Context for delegated task")
    
    # Communication details
    communication_protocol: Optional[str] = Field(
        default=None, 
        description="Protocol used for delegation"
    )
    message_size: Optional[int] = Field(default=None, description="Size of delegation message")
    
    # Failure reasons
    delegation_failure_reason: Optional[str] = Field(
        default=None, 
        description="Reason delegation failed"
    )
    target_unavailable: bool = Field(default=False, description="Whether target agent was unavailable")
    permission_denied: bool = Field(default=False, description="Whether delegation was denied")


class SynthesisErrorSchema(OrchestratorErrorSchema):
    """Schema for result synthesis failures."""
    
    # Synthesis details
    synthesis_method: Optional[str] = Field(default=None, description="Method used for synthesis")
    component_count: int = Field(default=0, description="Number of components to synthesize")
    
    # Component information
    completed_components: List[str] = Field(
        default_factory=list, 
        description="Components that completed successfully"
    )
    failed_components: List[str] = Field(
        default_factory=list, 
        description="Components that failed"
    )
    
    # LLM information
    synthesis_model: Optional[str] = Field(default=None, description="Model used for synthesis")
    synthesis_prompt_size: Optional[int] = Field(
        default=None, 
        description="Size of synthesis prompt"
    )
    
    # Failure details
    synthesis_failure_reason: Optional[str] = Field(
        default=None, 
        description="Reason synthesis failed"
    )
    inconsistency_detected: bool = Field(
        default=False, 
        description="Whether inconsistency in components was detected"
    )
    fallback_used: bool = Field(default=False, description="Whether fallback synthesis was used")
