"""Request schemas for API endpoints."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from mindflow_backend.schemas.core.common import LLMProvider


class AgentChatRequest(BaseModel):
    """Request for agent chat interaction."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    message: str = Field(min_length=1, max_length=100000, description="User message")
    provider: Optional[LLMProvider] = Field(default=None, description="LLM provider")
    model: Optional[str] = Field(default=None, description="Model name")
    session_id: Optional[str] = Field(default=None, alias="sessionId", description="Session ID")
    agent_type: Optional[str] = Field(default=None, description="Agent type to use")
    orchestrate: bool = Field(default=False, description="Whether to use orchestration")
    debug_steps: bool = Field(default=False, alias="debugSteps", description="Enable debug steps")


class SessionCreateRequest(BaseModel):
    """Request for creating a new session."""
    
    title: Optional[str] = Field(default=None, max_length=255, description="Session title")
    user_id: Optional[str] = Field(default=None, max_length=100, description="User identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class SessionUpdateRequest(BaseModel):
    """Request for updating a session."""
    
    title: Optional[str] = Field(default=None, max_length=255, description="New session title")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Session metadata")


class MessageAddRequest(BaseModel):
    """Request for adding a message to a session."""
    
    role: Literal["user", "assistant", "system"] = Field(description="Message role")
    content: str = Field(min_length=1, max_length=100000, description="Message content")
    provider: Optional[str] = Field(default=None, description="LLM provider")
    model: Optional[str] = Field(default=None, description="Model name")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Message metadata")


class OrchestrationRequest(BaseModel):
    """Request for task orchestration."""
    
    task_description: str = Field(min_length=10, max_length=10000, description="Task description")
    complexity_level: Optional[Literal["low", "medium", "high"]] = Field(
        default="medium", description="Task complexity level"
    )
    agent_sequence: Optional[list[str]] = Field(
        default=None, description="Specific agent sequence to use"
    )
    session_id: Optional[str] = Field(default=None, description="Session ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Orchestration metadata")


class TaskDecompositionRequest(BaseModel):
    """Request for task decomposition."""
    
    task_description: str = Field(min_length=10, max_length=10000, description="Task to decompose")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    complexity_level: Optional[Literal["low", "medium", "high"]] = Field(
        default="medium", description="Task complexity level"
    )
    max_subtasks: int = Field(default=10, ge=1, le=50, description="Maximum number of subtasks")


class PersonalitySelectionRequest(BaseModel):
    """Request for personality selection."""
    
    task_id: str = Field(description="Task identifier")
    task_description: str = Field(min_length=10, max_length=10000, description="Task description")
    task_complexity: Literal["low", "medium", "high"] = Field(description="Task complexity")
    current_personality: Optional[str] = Field(default=None, description="Current personality")
    context_requirements: Optional[list[str]] = Field(
        default=None, description="Required context"
    )


class ProviderConfigRequest(BaseModel):
    """Request for provider configuration."""
    
    api_endpoint: Optional[str] = Field(default=None, description="API endpoint URL")
    timeout: Optional[int] = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    max_tokens: Optional[int] = Field(default=4096, ge=1, le=100000, description="Max tokens")
    api_key: Optional[str] = Field(default=None, description="API key (if updating)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional config")


class ProviderTestRequest(BaseModel):
    """Request for testing provider connection."""
    
    provider_id: str = Field(description="Provider identifier")
    test_model: Optional[str] = Field(default=None, description="Model to test with")


class MemorySearchRequest(BaseModel):
    """Request for memory/context search."""
    
    query: str = Field(min_length=1, max_length=1000, description="Search query")
    session_id: str = Field(description="Session ID")
    agent_id: Optional[str] = Field(default=None, description="Agent ID filter")
    search_type: Literal["semantic", "keyword", "hybrid"] = Field(
        default="semantic", description="Search type"
    )
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum results")
    min_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum similarity score")
    token_range: Optional[tuple[int, int]] = Field(default=None, description="Token range filter")


class MemorySummaryRequest(BaseModel):
    """Request for memory summarization."""
    
    agent_id: str = Field(description="Agent identifier")
    session_id: str = Field(description="Session identifier")
    window_start: int = Field(ge=0, description="Window start token")
    window_end: int = Field(ge=1, description="Window end token")
    summary_type: Literal["auto", "key_points", "full"] = Field(
        default="auto", description="Summary type"
    )


class ContextWindowRequest(BaseModel):
    """Request for context window retrieval."""
    
    session_id: str = Field(description="Session identifier")
    window_start: int = Field(ge=0, description="Window start position")
    window_end: int = Field(ge=1, description="Window end position")
    include_metadata: bool = Field(default=True, description="Include metadata")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to return")
