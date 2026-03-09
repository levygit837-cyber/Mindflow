"""Chains API endpoints for MindFlow."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional, Any

from mindflow_backend.chains.factory import get_chain_factory, ChainRequest
from mindflow_backend.chains.catalog import list_available_chains, get_chain_info, find_chains_for_task
from mindflow_backend.api.controllers.base_controller import BaseController, require_auth, audit_log
from mindflow_backend.api.schemas.requests import ChainExecuteRequest, ChainCreateRequest
from mindflow_backend.api.schemas.responses import (
    ChainListResponse,
    ChainInfoResponse,
    ChainExecuteResponse,
    ChainStatsResponse,
    ChainRegistryResponse
)

router = APIRouter(prefix="/chains", tags=["chains"])

# Initialize controller
class ChainController(BaseController):
    """Controller for chain management operations."""
    
    def __init__(self):
        super().__init__()
        self.chain_factory = get_chain_factory()
    
    def get_chain_metadata(self, chain_id: str) -> Dict[str, Any]:
        """Get metadata for a specific chain."""
        metadata = self.chain_factory.registry.get_metadata(chain_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")
        
        return {
            "chain_id": metadata.chain_id,
            "name": metadata.name,
            "description": metadata.description,
            "version": metadata.version,
            "capabilities": [cap.value for cap in metadata.capabilities],
            "complexity": metadata.complexity.value,
            "estimated_execution_time": metadata.estimated_execution_time,
            "max_memory_usage": metadata.max_memory_usage,
            "required_agents": [agent.value for agent in metadata.required_agents],
            "default_config": metadata.default_config,
            "max_parallel_instances": metadata.max_parallel_instances,
            "timeout": metadata.timeout,
            "retry_attempts": metadata.retry_attempts,
        }
    
    def format_chain_list(self, chains: List) -> List[Dict[str, Any]]:
        """Format chain list for response."""
        return [
            {
                "chain_id": metadata.chain_id,
                "name": metadata.name,
                "description": metadata.description,
                "capabilities": [cap.value for cap in metadata.capabilities],
                "complexity": metadata.complexity.value,
                "estimated_execution_time": metadata.estimated_execution_time,
                "required_agents": [agent.value for agent in metadata.required_agents],
            }
            for metadata in chains
        ]

chain_controller = ChainController()


@router.get("/", response_model=ChainListResponse)
async def list_chains(
    capability: Optional[str] = None,
    complexity: Optional[str] = None
):
    """List all available chains with optional filtering."""
    try:
        factory = chain_controller.chain_factory
        
        # Get chains with optional filtering
        if capability:
            from mindflow_backend.chains.factory import ChainCapability
            chains = factory.registry.list_chains(ChainCapability(capability))
        elif complexity:
            from mindflow_backend.chains.factory import ChainComplexity
            chains = factory.registry.list_chains()
            chains = [c for c in chains if c.complexity == ChainComplexity(complexity)]
        else:
            chains = factory.registry.list_chains()
        
        formatted_chains = chain_controller.format_chain_list(chains)
        
        return ChainListResponse(
            success=True,
            message="Chains retrieved successfully",
            chains=formatted_chains,
            total=len(formatted_chains)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chain_id}", response_model=ChainInfoResponse)
async def get_chain_info(chain_id: str):
    """Get detailed information about a specific chain."""
    try:
        metadata = chain_controller.get_chain_metadata(chain_id)
        
        # Get execution statistics
        stats = chain_controller.chain_factory.get_chain_stats(chain_id)
        
        return ChainInfoResponse(
            success=True,
            message="Chain info retrieved successfully",
            chain=metadata,
            stats=stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chain_id}/execute", response_model=ChainExecuteResponse)
async def execute_chain(
    chain_id: str,
    request: ChainExecuteRequest
):
    """Execute a specific chain with context."""
    try:
        # Verify chain exists
        chain_controller.get_chain_metadata(chain_id)
        
        # Create chain request
        chain_request = ChainRequest(
            chain_id=chain_id,
            config=request.config,
            execution_context=request.execution_context,
            priority=request.priority,
            request_id=request.request_id
        )
        
        # Execute chain
        result = await chain_controller.chain_factory.execute_chain(
            chain_request, 
            request.context
        )
        
        return ChainExecuteResponse(
            success=True,
            message="Chain executed successfully",
            chain_id=chain_id,
            execution_id=result.get("execution_metadata", {}).get("execution_id"),
            response=result.get("response"),
            error=result.get("error"),
            execution_metadata=result.get("execution_metadata")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chain_id}/stats", response_model=ChainStatsResponse)
async def get_chain_statistics(chain_id: str):
    """Get execution statistics for a specific chain."""
    try:
        # Verify chain exists
        chain_controller.get_chain_metadata(chain_id)
        
        # Get statistics
        stats = chain_controller.chain_factory.get_chain_stats(chain_id)
        
        return ChainStatsResponse(
            success=True,
            message="Statistics retrieved successfully",
            chain_id=chain_id,
            stats=stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/find", response_model=ChainListResponse)
async def find_chains_for_task(
    task_type: str,
    complexity: Optional[str] = None,
    required_capabilities: Optional[List[str]] = None
):
    """Find chains suitable for a specific task type."""
    try:
        factory = chain_controller.chain_factory
        
        # Convert complexity if provided
        complexity_enum = None
        if complexity:
            from mindflow_backend.chains.factory import ChainComplexity
            complexity_enum = ChainComplexity(complexity)
        
        # Convert capabilities if provided
        capability_enums = None
        if required_capabilities:
            from mindflow_backend.chains.factory import ChainCapability
            capability_enums = [ChainCapability(cap) for cap in required_capabilities]
        
        # Find suitable chains
        chains = factory.registry.find_chains_for_task(
            task_type=task_type,
            complexity=complexity_enum,
            required_capabilities=capability_enums
        )
        
        formatted_chains = chain_controller.format_chain_list(chains)
        
        return ChainListResponse(
            success=True,
            message=f"Chains found for task type: {task_type}",
            chains=formatted_chains,
            total=len(formatted_chains)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry/info", response_model=ChainRegistryResponse)
async def get_registry_info():
    """Get information about the chain registry."""
    try:
        registry_info = chain_controller.chain_factory.get_registry_info()
        
        return ChainRegistryResponse(
            success=True,
            message="Registry info retrieved successfully",
            registry_info=registry_info
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
