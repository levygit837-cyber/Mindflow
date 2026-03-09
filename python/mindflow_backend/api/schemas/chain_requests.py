"""Request schemas for Chains API."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class ChainExecuteRequest(BaseModel):
    """Request to execute a chain."""
    
    context: Dict[str, Any] = Field(..., description="Context data for chain execution")
    config: Optional[Dict[str, Any]] = Field(None, description="Chain configuration overrides")
    execution_context: Optional[Dict[str, Any]] = Field(None, description="Additional execution context")
    priority: int = Field(0, description="Execution priority (higher = more priority)")
    request_id: Optional[str] = Field(None, description="Unique request identifier")


class ChainCreateRequest(BaseModel):
    """Request to create a chain instance."""
    
    chain_id: str = Field(..., description="Chain identifier")
    config: Optional[Dict[str, Any]] = Field(None, description="Chain configuration")
    execution_context: Optional[Dict[str, Any]] = Field(None, description="Execution context")
    priority: int = Field(0, description="Creation priority")
