"""Response schemas for Chains API."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class ChainListResponse(BaseModel):
    """Response for chain listing operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    chains: List[Dict[str, Any]] = Field(..., description="List of chain metadata")
    total: int = Field(..., description="Total number of chains")


class ChainInfoResponse(BaseModel):
    """Response for chain information operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    chain: Dict[str, Any] = Field(..., description="Chain metadata")
    stats: Dict[str, Any] = Field(..., description="Chain execution statistics")


class ChainExecuteResponse(BaseModel):
    """Response for chain execution operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    chain_id: str = Field(..., description="ID of the executed chain")
    execution_id: Optional[str] = Field(None, description="Execution identifier")
    response: Optional[str] = Field(None, description="Chain execution response")
    error: Optional[str] = Field(None, description="Execution error if any")
    execution_metadata: Optional[Dict[str, Any]] = Field(None, description="Execution metadata")


class ChainStatsResponse(BaseModel):
    """Response for chain statistics operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    chain_id: str = Field(..., description="Chain identifier")
    stats: Dict[str, Any] = Field(..., description="Chain execution statistics")


class ChainRegistryResponse(BaseModel):
    """Response for chain registry information operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    registry_info: Dict[str, Any] = Field(..., description="Registry information")
