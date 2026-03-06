"""gRPC request schemas."""

from typing import Literal
from pydantic import BaseModel, Field

from omnimind_backend.schemas.core.common import LLMProvider


class GrpcChatStreamRequest(BaseModel):
    """gRPC chat stream request schema."""
    session_id: str = Field(description="Session identifier")
    message: str = Field(min_length=1, max_length=100000, description="Message content")
    provider: LLMProvider | None = Field(default=None, description="LLM provider")
    model: str | None = Field(default=None, description="Model name")
    run_id: str | None = Field(default=None, description="Run identifier")
    orchestrate: bool = Field(default=False, description="Whether to orchestrate the response")
    agent_type: str | None = Field(default=None, description="Type of agent to use")
    debug_steps: bool = Field(default=False, description="Whether to include debug steps")
    timeout_seconds: int = Field(default=300, description="Request timeout in seconds")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")
