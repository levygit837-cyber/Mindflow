"""Tool execution schemas for MindFlow backend.

Provides schemas for tool execution context, results,
and execution tracking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from mindflow_backend.schemas.orchestration.orchestrator import AgentType


class ToolExecutionContext(BaseModel):
    """Context information for tool execution."""
    
    tool_name: str = Field(..., description="Name of executing tool")
    agent_type: AgentType = Field(..., description="Type of agent executing tool")
    parameters: Dict[str, Any] = Field(..., description="Execution parameters")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
    timeout_seconds: Optional[int] = Field(default=None, description="Execution timeout")
    retry_count: int = Field(default=0, description="Current retry attempt")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        use_enum_values = True


class ToolExecutionResult(BaseModel):
    """Standardized result format for tool execution."""
    
    success: bool = Field(..., description="Whether execution was successful")
    result: Optional[Any] = Field(default=None, description="Main result data")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tool_name: str = Field(..., description="Name of executed tool")
    execution_time_ms: int = Field(default=0, description="Execution time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
    cacheable: bool = Field(default=True, description="Whether result can be cached")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    
    class Config:
        use_enum_values = True


class ToolExecutionStats(BaseModel):
    """Execution statistics for a tool."""
    
    tool_name: str = Field(..., description="Tool name")
    total_executions: int = Field(default=0, description="Total number of executions")
    successful_executions: int = Field(default=0, description="Number of successful executions")
    failed_executions: int = Field(default=0, description="Number of failed executions")
    total_execution_time_ms: int = Field(default=0, description="Total execution time in milliseconds")
    average_execution_time_ms: float = Field(default=0.0, description="Average execution time in milliseconds")
    last_execution: Optional[datetime] = Field(default=None, description="Last execution timestamp")
    success_rate: float = Field(default=0.0, description="Success rate (0.0 to 1.0)")
    
    class Config:
        use_enum_values = True


class ToolExecutionRequest(BaseModel):
    """Request for tool execution."""
    
    tool_name: str = Field(..., description="Name of tool to execute")
    agent_type: AgentType = Field(..., description="Type of agent executing tool")
    parameters: Dict[str, Any] = Field(..., description="Execution parameters")
    context: Optional[ToolExecutionContext] = Field(default=None, description="Execution context")
    timeout_seconds: Optional[int] = Field(default=None, description="Execution timeout")
    bypass_cache: bool = Field(default=False, description="Bypass result cache")
    dry_run: bool = Field(default=False, description="Dry run (validate only)")
    
    class Config:
        use_enum_values = True


class ToolExecutionBatch(BaseModel):
    """Batch execution request for multiple tools."""
    
    requests: List[ToolExecutionRequest] = Field(..., description="Execution requests")
    max_concurrent: int = Field(default=5, description="Maximum concurrent executions")
    fail_fast: bool = Field(default=False, description="Stop on first failure")
    timeout_seconds: Optional[int] = Field(default=None, description="Overall timeout")
    
    class Config:
        use_enum_values = True


class ToolExecutionBatchResult(BaseModel):
    """Results from batch tool execution."""
    
    total_requests: int = Field(..., description="Total number of requests")
    successful_executions: int = Field(default=0, description="Number of successful executions")
    failed_executions: int = Field(default=0, description="Number of failed executions")
    results: List[ToolExecutionResult] = Field(..., description="Individual execution results")
    total_execution_time_ms: int = Field(default=0, description="Total execution time")
    batch_id: str = Field(..., description="Batch identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Batch execution timestamp")
    
    class Config:
        use_enum_values = True


class ToolCacheEntry(BaseModel):
    """Cache entry for tool execution results."""
    
    tool_name: str = Field(..., description="Tool name")
    cache_key: str = Field(..., description="Cache key")
    result: ToolExecutionResult = Field(..., description="Cached result")
    created_at: datetime = Field(default_factory=datetime.now, description="Cache creation time")
    last_accessed: datetime = Field(default_factory=datetime.now, description="Last access time")
    access_count: int = Field(default=0, description="Number of accesses")
    ttl_seconds: int = Field(default=300, description="Time-to-live in seconds")
    size_bytes: int = Field(default=0, description="Cache entry size in bytes")
    
    class Config:
        use_enum_values = True


def create_execution_context(
    tool_name: str,
    agent_type: AgentType,
    parameters: Dict[str, Any],
    **kwargs
) -> ToolExecutionContext:
    """Create a ToolExecutionContext from basic parameters.
    
    Args:
        tool_name: Name of executing tool
        agent_type: Type of agent executing tool
        parameters: Execution parameters
        **kwargs: Additional context properties
        
    Returns:
        ToolExecutionContext instance
    """
    return ToolExecutionContext(
        tool_name=tool_name,
        agent_type=agent_type,
        parameters=parameters,
        **kwargs
    )


def create_execution_result(
    success: bool,
    tool_name: str,
    result: Optional[Any] = None,
    error: Optional[str] = None,
    execution_time_ms: int = 0,
    **kwargs
) -> ToolExecutionResult:
    """Create a ToolExecutionResult from basic parameters.
    
    Args:
        success: Whether execution was successful
        tool_name: Name of executed tool
        result: Main result data
        error: Error message if execution failed
        execution_time_ms: Execution time in milliseconds
        **kwargs: Additional result properties
        
    Returns:
        ToolExecutionResult instance
    """
    return ToolExecutionResult(
        success=success,
        result=result,
        error=error,
        tool_name=tool_name,
        execution_time_ms=execution_time_ms,
        **kwargs
    )
