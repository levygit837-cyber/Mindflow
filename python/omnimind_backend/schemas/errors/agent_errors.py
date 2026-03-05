"""Agent-specific error schemas.

Specialized error schemas for agent execution, context retrieval,
and tool operation failures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from .base import ErrorSchema, ErrorContext, ErrorSeverity


class AgentErrorSchema(ErrorSchema):
    """Base schema for agent-related errors."""
    
    # Agent identification
    agent_type: Optional[str] = Field(default=None, description="Type of agent")
    agent_id: Optional[str] = Field(default=None, description="Agent instance ID")
    personality: Optional[str] = Field(default=None, description="Agent personality")
    
    # Execution context
    task_id: Optional[str] = Field(default=None, description="Task being executed")
    session_id: Optional[str] = Field(default=None, description="User session ID")
    
    class Config:
        extra = "allow"


class AgentExecutionErrorSchema(AgentErrorSchema):
    """Schema for agent execution failures."""
    
    # Execution details
    execution_phase: Optional[str] = Field(
        default=None, 
        description="Phase of execution where error occurred"
    )
    tool_being_used: Optional[str] = Field(
        default=None, 
        description="Tool being executed when error occurred"
    )
    
    # Resource usage
    tokens_used: Optional[int] = Field(default=None, description="Tokens consumed before failure")
    execution_time_ms: Optional[int] = Field(default=None, description="Execution time in ms")
    
    # Recovery suggestions
    suggested_actions: List[str] = Field(
        default_factory=list, 
        description="Suggested recovery actions"
    )


class AgentTimeoutErrorSchema(AgentErrorSchema):
    """Schema for agent timeout errors."""
    
    # Timeout details
    timeout_seconds: float = Field(description="Timeout limit in seconds")
    actual_duration_ms: Optional[int] = Field(default=None, description="Actual duration before timeout")
    
    # What was being processed
    operation_type: Optional[str] = Field(
        default=None, 
        description="Type of operation that timed out"
    )
    input_size: Optional[int] = Field(
        default=None, 
        description="Size of input being processed"
    )
    
    # Recovery options
    can_increase_timeout: bool = Field(
        default=False, 
        description="Whether timeout can be increased"
    )
    suggested_timeout: Optional[float] = Field(
        default=None, 
        description="Suggested new timeout value"
    )


class ContextRetrievalErrorSchema(AgentErrorSchema):
    """Schema for context retrieval failures."""
    
    # Retrieval details
    retrieval_method: Optional[str] = Field(
        default=None, 
        description="Method used for context retrieval"
    )
    query_type: Optional[str] = Field(default=None, description="Type of query being executed")
    
    # Vector store information
    vector_store: Optional[str] = Field(default=None, description="Vector store being used")
    index_name: Optional[str] = Field(default=None, description="Index being queried")
    
    # Query information
    query_embedding_size: Optional[int] = Field(default=None, description="Size of query embedding")
    search_limit: Optional[int] = Field(default=None, description="Search result limit")
    
    # Failure details
    failure_reason: Optional[str] = Field(
        default=None, 
        description="Specific reason for retrieval failure"
    )
    partial_results: bool = Field(
        default=False, 
        description="Whether partial results were obtained"
    )


class ToolExecutionErrorSchema(AgentErrorSchema):
    """Schema for tool execution failures."""
    
    # Tool information
    tool_name: str = Field(description="Name of the tool that failed")
    tool_type: Optional[str] = Field(default=None, description="Type/category of tool")
    
    # Execution details
    tool_arguments: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Arguments passed to tool"
    )
    execution_environment: Optional[str] = Field(
        default=None, 
        description="Environment where tool was executed"
    )
    
    # Failure information
    tool_error_code: Optional[str] = Field(
        default=None, 
        description="Error code from tool itself"
    )
    tool_error_message: Optional[str] = Field(
        default=None, 
        description="Error message from tool"
    )
    
    # Safety/security
    safety_violation: bool = Field(
        default=False, 
        description="Whether error was due to safety violation"
    )
    security_blocked: bool = Field(
        default=False, 
        description="Whether tool execution was blocked for security"
    )


class PersonalitySelectionErrorSchema(AgentErrorSchema):
    """Schema for agent personality selection failures."""
    
    # Selection details
    task_description: Optional[str] = Field(
        default=None, 
        description="Description of task requiring personality selection"
    )
    analysis_method: Optional[str] = Field(
        default=None, 
        description="Method used for personality analysis"
    )
    
    # Candidate personalities
    candidate_personalities: List[str] = Field(
        default_factory=list, 
        description="Personalities that were considered"
    )
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict, 
        description="Confidence scores for each personality"
    )
    
    # Failure reason
    selection_failure_reason: Optional[str] = Field(
        default=None, 
        description="Why personality selection failed"
    )
    ambiguity_detected: bool = Field(
        default=False, 
        description="Whether selection failed due to ambiguity"
    )


class MemoryOperationErrorSchema(AgentErrorSchema):
    """Schema for memory operation failures."""
    
    # Memory operation details
    operation_type: str = Field(description="Type of memory operation")
    memory_store: Optional[str] = Field(default=None, description="Memory store being used")
    
    # Data information
    data_size: Optional[int] = Field(default=None, description="Size of data being processed")
    memory_key: Optional[str] = Field(default=None, description="Memory key being accessed")
    
    # Failure details
    operation_phase: Optional[str] = Field(
        default=None, 
        description="Phase of memory operation that failed"
    )
    data_corruption: bool = Field(
        default=False, 
        description="Whether data corruption was detected"
    )


class CacheErrorSchema(AgentErrorSchema):
    """Schema for cache operation failures."""
    
    # Cache details
    cache_operation: str = Field(description="Type of cache operation")
    cache_key: Optional[str] = Field(default=None, description="Cache key being accessed")
    cache_backend: Optional[str] = Field(default=None, description="Cache backend being used")
    
    # Data information
    data_size: Optional[int] = Field(default=None, description="Size of data being cached")
    ttl_seconds: Optional[int] = Field(default=None, description="TTL for cache entry")
    
    # Failure information
    backend_error: Optional[str] = Field(
        default=None, 
        description="Error from cache backend"
    )
    connection_failed: bool = Field(
        default=False, 
        description="Whether cache connection failed"
    )
