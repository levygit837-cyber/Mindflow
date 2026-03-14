"""Chain Factory System - Advanced chain creation and management.

This module provides a sophisticated factory system that gives the Orchestrator
full control over chain creation, configuration, and execution lifecycle.

Key features:
- Dynamic chain creation with custom configurations
- Chain registry with metadata and capabilities
- Execution lifecycle management
- Chain validation and health checks
- Performance monitoring and caching
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Dict, List, Optional, Type, Union
import time
import asyncio
from functools import lru_cache

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType

_logger = get_logger(__name__)


class ChainCapability(StrEnum):
    """Capabilities that chains can declare."""
    
    ANALYSIS = "analysis"
    CODING = "coding"
    RESEARCH = "research"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    PARALLEL_EXECUTION = "parallel_execution"
    CONDITIONAL_BRANCHING = "conditional_branching"
    ADAPTIVE_WORKFLOW = "adaptive_workflow"
    CONTEXT_AWARE = "context_aware"
    MULTI_AGENT = "multi_agent"


class ChainComplexity(StrEnum):
    """Complexity levels for chains."""
    
    LOW = "low"        # Simple, linear workflows
    MEDIUM = "medium"  # Multi-step with some branching
    HIGH = "high"     # Complex workflows with parallel execution
    EXTREME = "extreme" # Highly dynamic, adaptive workflows


@dataclass(frozen=True, slots=True)
class ChainMetadata:
    """Metadata for chain registration."""
    
    chain_id: str
    name: str
    description: str
    version: str = "1.0.0"
    
    # Capabilities and characteristics
    capabilities: List[ChainCapability] = field(default_factory=list)
    complexity: ChainComplexity = ChainComplexity.MEDIUM
    
    # Resource requirements
    estimated_execution_time: float = 60.0  # seconds
    max_memory_usage: str = "512MB"
    required_agents: List[AgentType] = field(default_factory=list)
    
    # Configuration schema
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)
    
    # Execution constraints
    max_parallel_instances: int = 5
    timeout: float = 300.0
    retry_attempts: int = 3
    
    # Dependencies
    required_chains: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ChainRequest:
    """Request for chain creation."""
    
    chain_id: str
    config: Optional[Dict[str, Any]] = None
    execution_context: Optional[Dict[str, Any]] = None
    priority: int = 0  # Higher = more priority
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChainInstance:
    """Wrapper for chain instance with lifecycle management."""
    
    chain: Any
    metadata: ChainMetadata
    created_at: float
    last_used: Optional[float] = None
    execution_count: int = 0
    total_execution_time: float = 0.0
    is_active: bool = False
    
    def mark_used(self, execution_time: float) -> None:
        """Mark chain as used with execution time."""
        self.last_used = time.time()
        self.execution_count += 1
        self.total_execution_time += execution_time


class ChainRegistry:
    """Central registry for chain factories and metadata."""
    
    def __init__(self) -> None:
        self._factories: Dict[str, Callable] = {}
        self._metadata: Dict[str, ChainMetadata] = {}
        self._instances: Dict[str, ChainInstance] = {}
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
        
    def register(
        self,
        chain_id: str,
        factory: Callable,
        metadata: ChainMetadata,
    ) -> None:
        """Register a chain factory with metadata."""
        
        if chain_id in self._factories:
            _logger.warning("chain_already_registered", chain_id=chain_id)
            return
        
        self._factories[chain_id] = factory
        self._metadata[chain_id] = metadata
        self._execution_stats[chain_id] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "total_execution_time": 0.0,
            "last_execution": None,
        }
        
        _logger.info("chain_registered", chain_id=chain_id, complexity=metadata.complexity.value)
    
    def get_metadata(self, chain_id: str) -> Optional[ChainMetadata]:
        """Get metadata for a chain."""
        return self._metadata.get(chain_id)
    
    def list_chains(self, capability: Optional[ChainCapability] = None) -> List[ChainMetadata]:
        """List all registered chains, optionally filtered by capability."""
        
        chains = list(self._metadata.values())
        
        if capability:
            chains = [c for c in chains if capability in c.capabilities]
        
        return chains
    
    def find_chains_for_task(
        self,
        task_type: str,
        complexity: Optional[ChainComplexity] = None,
        required_capabilities: Optional[List[ChainCapability]] = None,
    ) -> List[ChainMetadata]:
        """Find suitable chains for a specific task."""
        
        suitable_chains = []
        
        for metadata in self._metadata.values():
            # Filter by complexity
            if complexity and metadata.complexity != complexity:
                continue
            
            # Filter by required capabilities
            if required_capabilities:
                if not all(cap in metadata.capabilities for cap in required_capabilities):
                    continue
            
            # Task type matching (simplified heuristic)
            if self._matches_task_type(metadata, task_type):
                suitable_chains.append(metadata)
        
        # Sort by complexity and estimated time
        suitable_chains.sort(key=lambda c: (c.complexity.value, c.estimated_execution_time))
        
        return suitable_chains
    
    def _matches_task_type(self, metadata: ChainMetadata, task_type: str) -> bool:
        """Check if chain matches task type using heuristics."""
        
        task_mapping = {
            "analysis": [ChainCapability.ANALYSIS],
            "coding": [ChainCapability.CODING],
            "research": [ChainCapability.RESEARCH],
            "synthesis": [ChainCapability.SYNTHESIS],
            "validation": [ChainCapability.VALIDATION],
            "complex": [ChainCapability.CONDITIONAL_BRANCHING, ChainCapability.ADAPTIVE_WORKFLOW],
        }
        
        required_caps = task_mapping.get(task_type.lower(), [])
        
        if not required_caps:
            return True  # No specific requirements
        
        return any(cap in metadata.capabilities for cap in required_caps)


class ChainFactory:
    """Advanced chain factory with lifecycle management."""
    
    def __init__(self) -> None:
        self.registry = ChainRegistry()
        self._cache: Dict[str, ChainInstance] = {}
        self._cache_size_limit = 50
        self._active_executions: Dict[str, asyncio.Lock] = {}
        
        # Auto-register built-in chains
        self._register_builtin_chains()
    
    def _register_builtin_chains(self) -> None:
        """Register built-in chains with their metadata."""
        
        # Analysis Chain
        from mindflow_backend.chains.templates.analysis_chain import create_analysis_chain, AnalysisChainConfig
        
        analysis_metadata = ChainMetadata(
            chain_id="analysis_task",
            name="Analysis Workflow",
            description="Multi-step analysis with context gathering and synthesis",
            capabilities=[ChainCapability.ANALYSIS, ChainCapability.CONTEXT_AWARE, ChainCapability.MULTI_AGENT],
            complexity=ChainComplexity.MEDIUM,
            estimated_execution_time=45.0,
            required_agents=[AgentType.ANALYST, AgentType.RESEARCHER],
            default_config={"enable_deep_analysis": True, "max_context_chars": 8000},
        )
        
        self.registry.register(
            "analysis_task",
            lambda config=None: create_analysis_chain(AnalysisChainConfig(**(config or {}))),
            analysis_metadata
        )
        
        # Coding Task Chain
        from mindflow_backend.chains.templates.coding_task_chain import CodingTaskChain, CodingTaskChainConfig
        
        coding_metadata = ChainMetadata(
            chain_id="coding_task",
            name="Coding Workflow",
            description="Analysis → Implementation → Code Review workflow",
            capabilities=[ChainCapability.CODING, ChainCapability.VALIDATION, ChainCapability.MULTI_AGENT],
            complexity=ChainComplexity.MEDIUM,
            estimated_execution_time=90.0,
            required_agents=[AgentType.ANALYST, AgentType.CODER],
            default_config={"use_deep_analysis": False},
        )
        
        self.registry.register(
            "coding_task",
            lambda config=None: CodingTaskChain(CodingTaskChainConfig(**(config or {}))),
            coding_metadata
        )
        
        # Conditional Workflow Chain
        from mindflow_backend.chains.templates.conditional_workflow_chain import (
            create_conditional_workflow_chain, ConditionalWorkflowConfig
        )
        
        conditional_metadata = ChainMetadata(
            chain_id="conditional_workflow",
            name="Conditional Workflow",
            description="Dynamic workflow with branching and parallel execution",
            capabilities=[
                ChainCapability.CONDITIONAL_BRANCHING,
                ChainCapability.PARALLEL_EXECUTION,
                ChainCapability.ADAPTIVE_WORKFLOW,
                ChainCapability.MULTI_AGENT
            ],
            complexity=ChainComplexity.HIGH,
            estimated_execution_time=120.0,
            required_agents=[AgentType.ANALYST, AgentType.RESEARCHER],
            default_config={"enable_parallel_paths": True, "confidence_threshold": 0.7},
        )
        
        self.registry.register(
            "conditional_workflow",
            lambda config=None: create_conditional_workflow_chain(ConditionalWorkflowConfig(**(config or {}))),
            conditional_metadata
        )
    
    async def create_chain(self, request: ChainRequest) -> ChainInstance:
        """Create a chain instance from request."""
        
        # Get factory and metadata
        factory = self.registry._factories.get(request.chain_id)
        metadata = self.registry.get_metadata(request.chain_id)
        
        if not factory or not metadata:
            raise ValueError(f"Unknown chain: {request.chain_id}")
        
        # Check execution limits
        if not self._can_execute_chain(request.chain_id):
            raise RuntimeError(f"Chain {request.chain_id} has reached execution limits")
        
        # Merge configurations
        config = dict(metadata.default_config)
        if request.config:
            config.update(request.config)
        
        # Create chain instance
        try:
            chain = factory(config)
            
            instance = ChainInstance(
                chain=chain,
                metadata=metadata,
                created_at=time.time(),
            )
            
            # Cache management
            self._manage_cache()
            
            _logger.info("chain_created", 
                        chain_id=request.chain_id,
                        config_keys=list(config.keys()),
                        request_id=request.request_id)
            
            return instance
            
        except Exception as e:
            _logger.error("chain_creation_failed", 
                         chain_id=request.chain_id,
                         error=str(e))
            raise
    
    async def execute_chain(
        self,
        request: ChainRequest,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a chain with full lifecycle management."""
        
        start_time = time.time()
        execution_id = request.request_id or f"exec_{int(start_time)}"
        
        # Check for concurrent execution limits
        if request.chain_id in self._active_executions:
            lock = self._active_executions[request.chain_id]
        else:
            lock = asyncio.Lock()
            self._active_executions[request.chain_id] = lock
        
        async with lock:
            try:
                # Create chain instance
                instance = await self.create_chain(request)
                instance.is_active = True
                
                # Update execution stats
                stats = self.registry._execution_stats[request.chain_id]
                stats["total_executions"] += 1
                stats["last_execution"] = start_time
                
                # Execute chain
                _logger.info("chain_execution_started", 
                            chain_id=request.chain_id,
                            execution_id=execution_id)
                
                # Add execution context to chain context
                execution_context = dict(context)
                if request.execution_context:
                    execution_context.update(request.execution_context)
                
                # Execute the chain
                result = await instance.chain.execute(execution_context)
                
                execution_time = time.time() - start_time
                
                # Update instance and stats
                instance.mark_used(execution_time)
                stats["total_execution_time"] += execution_time
                stats["average_execution_time"] = stats["total_execution_time"] / stats["total_executions"]
                
                if result.get("error"):
                    stats["failed_executions"] += 1
                else:
                    stats["successful_executions"] += 1
                
                instance.is_active = False
                
                _logger.info("chain_execution_completed",
                            chain_id=request.chain_id,
                            execution_id=execution_id,
                            execution_time=execution_time,
                            success=result.get("error") is None)
                
                # Add execution metadata to result
                result["execution_metadata"] = {
                    "chain_id": request.chain_id,
                    "execution_id": execution_id,
                    "execution_time": execution_time,
                    "chain_metadata": instance.metadata,
                }
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Update error stats
                stats = self.registry._execution_stats[request.chain_id]
                stats["failed_executions"] += 1
                stats["total_execution_time"] += execution_time
                stats["average_execution_time"] = stats["total_execution_time"] / stats["total_executions"]
                
                _logger.error("chain_execution_failed",
                             chain_id=request.chain_id,
                             execution_id=execution_id,
                             error=str(e),
                             execution_time=execution_time)
                
                return {
                    "response": "",
                    "error": f"Chain execution failed: {str(e)}",
                    "execution_metadata": {
                        "chain_id": request.chain_id,
                        "execution_id": execution_id,
                        "execution_time": execution_time,
                        "failed": True,
                    }
                }
            
            finally:
                # Cleanup active execution tracking
                if request.chain_id in self._active_executions:
                    del self._active_executions[request.chain_id]
    
    def _can_execute_chain(self, chain_id: str) -> bool:
        """Check if chain can be executed based on limits."""
        
        metadata = self.registry.get_metadata(chain_id)
        if not metadata:
            return False
        
        # Check concurrent execution limit
        active_count = sum(1 for instance in self._cache.values() 
                          if instance.is_active and instance.metadata.chain_id == chain_id)
        
        return active_count < metadata.max_parallel_instances
    
    def _manage_cache(self) -> None:
        """Manage chain instance cache size."""
        
        if len(self._cache) <= self._cache_size_limit:
            return
        
        # Remove least recently used instances
        sorted_instances = sorted(
            self._cache.values(),
            key=lambda i: (i.last_used or 0, i.created_at)
        )
        
        to_remove = sorted_instances[:len(self._cache) - self._cache_size_limit]
        
        for instance in to_remove:
            # Find and remove from cache
            for key, cached_instance in list(self._cache.items()):
                if cached_instance == instance:
                    del self._cache[key]
                    break
        
        _logger.info("chain_cache_cleanup", removed=len(to_remove))
    
    def get_chain_stats(self, chain_id: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics for chains."""
        
        if chain_id:
            return self.registry._execution_stats.get(chain_id, {})
        
        return self.registry._execution_stats
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get information about the chain registry."""
        
        return {
            "total_chains": len(self.registry._factories),
            "chains_by_complexity": {
                complexity.value: len([
                    m for m in self.registry._metadata.values()
                    if m.complexity == complexity
                ])
                for complexity in ChainComplexity
            },
            "chains_by_capability": {
                capability.value: len([
                    m for m in self.registry._metadata.values()
                    if capability in m.capabilities
                ])
                for capability in ChainCapability
            },
            "cache_size": len(self._cache),
            "active_executions": len(self._active_executions),
        }


# Global factory instance
_chain_factory = ChainFactory()


def get_chain_factory() -> ChainFactory:
    """Get the global chain factory instance."""
    return _chain_factory


# Convenience functions for backward compatibility
async def create_and_execute_chain(
    chain_id: str,
    context: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function to create and execute a chain."""
    
    request = ChainRequest(
        chain_id=chain_id,
        config=config,
        **kwargs
    )
    
    factory = get_chain_factory()
    return await factory.execute_chain(request, context)


def get_available_chains(task_type: Optional[str] = None) -> List[ChainMetadata]:
    """Get list of available chains, optionally filtered by task type."""
    
    factory = get_chain_factory()
    
    if task_type:
        return factory.registry.find_chains_for_task(task_type)
    
    return factory.registry.list_chains()


def get_chain_metadata(chain_id: str) -> Optional[ChainMetadata]:
    """Get metadata for a specific chain."""
    
    factory = get_chain_factory()
    return factory.registry.get_metadata(chain_id)
