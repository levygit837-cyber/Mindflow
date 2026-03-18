"""Result schema for queue message processing."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MessageProcessingResult(BaseModel):
    """Normalized result returned by queue consumers."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
