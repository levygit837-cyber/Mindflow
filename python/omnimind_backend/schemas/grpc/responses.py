"""gRPC response schemas."""

from typing import Any
from pydantic import BaseModel, Field

from omnimind_backend.schemas.chat.agent import StreamEvent


class GrpcStreamEvent(BaseModel):
    """gRPC stream event schema."""
    event: StreamEvent = Field(description="Stream event data")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    timestamp: str = Field(description="Event timestamp in ISO format")
    sequence_number: int = Field(description="Event sequence number")
    is_final: bool = Field(default=False, description="Whether this is the final event")
