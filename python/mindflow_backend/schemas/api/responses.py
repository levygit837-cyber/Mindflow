"""Response schemas for API endpoints."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from .common import BaseResponse, PaginationResponse


class AgentResponse(BaseResponse):
    """Response for agent operations."""
    
    agent_type: Optional[str] = Field(default=None, description="Agent type used")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    response: Optional[str] = Field(default=None, description="Agent response")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    capabilities: Optional[list[str]] = Field(default=None, description="Agent capabilities")


class SessionResponse(BaseResponse):
    """Response for session operations."""
    
    id: str = Field(description="Session ID")
    title: Optional[str] = Field(default=None, description="Session title")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    message_count: Optional[int] = Field(default=None, description="Number of messages")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class MessageResponse(BaseResponse):
    """Response for message operations."""
    
    id: Optional[int] = Field(default=None, description="Message ID")
    session_id: str = Field(description="Session ID")
    role: str = Field(description="Message role")
    content: str = Field(description="Message content")
    provider: Optional[str] = Field(default=None, description="LLM provider")
    model: Optional[str] = Field(default=None, description="Model name")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    token_count: Optional[int] = Field(default=None, description="Token count")


class SessionListResponse(PaginationResponse[SessionResponse]):
    """Paginated response for session listings."""
    pass


class OrchestrationResponse(BaseResponse):
    """Response for orchestration operations."""
    
    task_id: Optional[str] = Field(default=None, description="Task ID")
    execution_id: Optional[str] = Field(default=None, description="Execution ID")
    status: str = Field(description="Execution status")
    sub_tasks: Optional[list[dict[str, Any]]] = Field(default=None, description="Sub-tasks")
    results: Optional[list[dict[str, Any]]] = Field(default=None, description="Execution results")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Orchestration metadata")


class TaskDecompositionResponse(BaseResponse):
    """Response for task decomposition."""
    
    task_id: str = Field(description="Task ID")
    description: str = Field(description="Original task description")
    sub_tasks: list[dict[str, Any]] = Field(description="Decomposed sub-tasks")
    complexity_level: str = Field(description="Task complexity level")
    dependencies: Optional[list[dict[str, Any]]] = Field(default=None, description="Task dependencies")
    estimated_duration: Optional[str] = Field(default=None, description="Estimated duration")


class SpecialistSelectionResponse(BaseResponse):
    """Response for specialist selection."""
    
    task_id: str = Field(description="Task ID")
    selected_specialist: str = Field(description="Selected specialist")
    rationale: str = Field(description="Selection rationale")
    confidence: float = Field(description="Selection confidence")
    alternatives: Optional[list[dict[str, Any]]] = Field(default=None, description="Alternative specialists")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Selection metadata")


class ProviderResponse(BaseResponse):
    """Response for provider operations."""
    
    provider_id: str = Field(description="Provider ID")
    name: Optional[str] = Field(default=None, description="Provider name")
    status: Optional[str] = Field(default=None, description="Provider status")
    models: Optional[list[str]] = Field(default=None, description="Available models")
    config: Optional[dict[str, Any]] = Field(default=None, description="Provider configuration")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProviderListResponse(BaseResponse):
    """Response for provider listing."""
    
    providers: list[ProviderResponse] = Field(description="List of providers")
    total: int = Field(description="Total number of providers")


class ProviderTestResponse(BaseResponse):
    """Response for provider connection test."""
    
    provider_id: str = Field(description="Provider ID")
    status: str = Field(description="Test status")
    latency_ms: Optional[int] = Field(default=None, description="Connection latency")
    tested_at: Optional[str] = Field(default=None, description="Test timestamp")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Test metadata")


class MemoryResponse(BaseResponse):
    """Response for memory operations."""
    
    agent_id: str = Field(description="Agent ID")
    session_id: str = Field(description="Session ID")
    memory_events: Optional[list[dict[str, Any]]] = Field(default=None, description="Memory events")
    token_count: Optional[int] = Field(default=None, description="Total token count")
    window_index: Optional[int] = Field(default=None, description="Current window index")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Memory metadata")


class MemorySearchResponse(BaseResponse):
    """Response for memory search operations."""
    
    query: str = Field(description="Search query")
    results: list[dict[str, Any]] = Field(description="Search results")
    total_found: int = Field(description="Total items found")
    search_type: str = Field(description="Search type used")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")


class MemorySummaryResponse(BaseResponse):
    """Response for memory summarization."""
    
    agent_id: str = Field(description="Agent ID")
    session_id: str = Field(description="Session ID")
    window_range: tuple[int, int] = Field(description="Summarized window range")
    summary: str = Field(description="Generated summary")
    key_points: list[str] = Field(description="Key points extracted")
    coverage_ratio: float = Field(description="Coverage ratio")
    token_count: int = Field(description="Tokens summarized")
    created_at: Optional[str] = Field(default=None, description="Summary creation timestamp")


class ContextWindowResponse(BaseResponse):
    """Response for context window operations."""
    
    session_id: str = Field(description="Session ID")
    window_start: int = Field(description="Window start position")
    window_end: int = Field(description="Window end position")
    content: str = Field(description="Window content")
    events: Optional[list[dict[str, Any]]] = Field(default=None, description="Window events")
    token_count: int = Field(description="Token count in window")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Window metadata")


class ExecutionStatusResponse(BaseResponse):
    """Response for execution status queries."""
    
    execution_id: str = Field(description="Execution ID")
    status: str = Field(description="Execution status")
    progress: Optional[float] = Field(default=None, description="Progress percentage")
    tasks_completed: Optional[int] = Field(default=None, description="Completed tasks")
    total_tasks: Optional[int] = Field(default=None, description="Total tasks")
    started_at: Optional[str] = Field(default=None, description="Start timestamp")
    completed_at: Optional[str] = Field(default=None, description="Completion timestamp")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Execution metadata")


class FallbackResponse(BaseResponse):
    """Response for provider fallback operations."""
    
    failed_provider: str = Field(description="Failed provider ID")
    fallback_triggered: bool = Field(description="Whether fallback was triggered")
    next_provider: Optional[str] = Field(default=None, description="Next provider ID")
    error: Optional[str] = Field(default=None, description="Original error")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Fallback metadata")
