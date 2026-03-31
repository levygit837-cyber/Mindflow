"""Request schemas for Chains API."""

from typing import Any

from pydantic import BaseModel, Field


class ChainExecuteRequest(BaseModel):
    """Request to execute a chain."""
    
    context: dict[str, Any] = Field(..., description="Context data for chain execution")
    config: dict[str, Any] | None = Field(None, description="Chain configuration overrides")
    execution_context: dict[str, Any] | None = Field(None, description="Additional execution context")
    priority: int = Field(0, description="Execution priority (higher = more priority)")
    request_id: str | None = Field(None, description="Unique request identifier")


class ChainCreateRequest(BaseModel):
    """Request to create a chain instance."""
    
    chain_id: str = Field(..., description="Chain identifier")
    config: dict[str, Any] | None = Field(None, description="Chain configuration")
    execution_context: dict[str, Any] | None = Field(None, description="Execution context")
    priority: int = Field(0, description="Creation priority")
