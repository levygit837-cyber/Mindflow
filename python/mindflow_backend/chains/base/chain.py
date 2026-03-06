"""Base chain classes for MindFlow orchestration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from mindflow_backend.chains.base.step import ChainStep, StepResult, StepStatus, StepMetrics


class ChainType(StrEnum):
    """Types of chains supported by the system."""
    
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOPING = "looping"
    ADAPTIVE = "adaptive"
    CUSTOM = "custom"


class ChainStatus(StrEnum):
    """Status of chain execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ChainConfig(BaseModel):
    """Configuration for chain execution."""
    
    chain_type: ChainType = ChainType.SEQUENTIAL
    max_execution_time: Optional[float] = Field(default=300.0, gt=0.0)
    enable_streaming: bool = False
    enable_parallel_execution: bool = False
    retry_failed_steps: bool = True
    max_step_retries: int = Field(default=3, ge=0)
    continue_on_step_failure: bool = False
    
    # Resource limits
    max_total_tokens: Optional[int] = Field(default=None, gt=0)
    max_memory_usage: Optional[str] = None  # e.g., "1GB"
    
    # Monitoring and debugging
    enable_metrics: bool = True
    enable_step_logging: bool = True
    save_intermediate_results: bool = False
    
    # Custom parameters
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class ChainMetrics(BaseModel):
    """Metrics collected during chain execution."""
    
    chain_id: str
    execution_id: str
    
    # Timing metrics
    total_execution_time: float = 0.0
    average_step_time: float = 0.0
    
    # Step metrics
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    
    # Resource metrics
    total_tokens_used: int = 0
    peak_memory_usage: Optional[float] = None
    
    # Execution details
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    step_results: List[StepResult] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class BaseChain(ABC):
    """Abstract base class for all chains in MindFlow."""
    
    def __init__(
        self,
        chain_id: str,
        config: Optional[ChainConfig] = None,
        description: str = ""
    ) -> None:
        self.chain_id = chain_id
        self.config = config or ChainConfig()
        self.description = description
        self.steps: List[ChainStep] = []
        self.step_metrics: Dict[str, StepMetrics] = {}
        self.status = ChainStatus.PENDING
        self._is_initialized = False
    
    @property
    @abstractmethod
    def chain_type(self) -> ChainType:
        """Return the type of this chain."""
        ...
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the chain with the given context."""
        ...
    
    @abstractmethod
    def validate(self) -> List[str]:
        """Validate the chain structure and configuration."""
        ...
    
    def add_step(self, step: ChainStep) -> None:
        """Add a step to the chain."""
        if step.step_id in [s.step_id for s in self.steps]:
            raise ValueError(f"Step {step.step_id} already exists in chain")
        
        self.steps.append(step)
        self.step_metrics[step.step_id] = StepMetrics(step_id=step.step_id)
    
    def remove_step(self, step_id: str) -> bool:
        """Remove a step from the chain."""
        for i, step in enumerate(self.steps):
            if step.step_id == step_id:
                del self.steps[i]
                if step_id in self.step_metrics:
                    del self.step_metrics[step_id]
                return True
        return False
    
    def get_step(self, step_id: str) -> Optional[ChainStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_steps(self) -> List[ChainStep]:
        """Get all steps in the chain."""
        return list(self.steps)
    
    def get_step_order(self) -> List[str]:
        """Get the execution order of steps."""
        # Default implementation returns steps in added order
        return [step.step_id for step in self.steps]
    
    async def initialize(self) -> None:
        """Initialize the chain (called once before first execution)."""
        if self._is_initialized:
            return
        
        await self._on_initialize()
        self._is_initialized = True
    
    async def _on_initialize(self) -> None:
        """Override this method for custom initialization logic."""
        pass
    
    def get_chain_info(self) -> Dict[str, Any]:
        """Get information about the chain."""
        return {
            "chain_id": self.chain_id,
            "chain_type": self.chain_type.value,
            "description": self.description,
            "status": self.status.value,
            "step_count": len(self.steps),
            "config": self.config.dict(),
            "steps": [step.dict() for step in self.steps],
            "is_initialized": self._is_initialized,
        }
    
    def get_metrics(self) -> ChainMetrics:
        """Get execution metrics for the chain."""
        total_tokens = sum(metrics.total_tokens_used for metrics in self.step_metrics.values())
        total_execution_time = sum(metrics.total_execution_time for metrics in self.step_metrics.values())
        
        return ChainMetrics(
            chain_id=self.chain_id,
            execution_id="",  # Would be set during execution
            total_execution_time=total_execution_time,
            average_step_time=total_execution_time / len(self.steps) if self.steps else 0.0,
            total_steps=len(self.steps),
            completed_steps=sum(1 for m in self.step_metrics.values() if m.success_count > 0),
            failed_steps=sum(1 for m in self.step_metrics.values() if m.failure_count > 0),
            skipped_steps=0,  # Would be tracked during execution
            total_tokens_used=total_tokens,
            step_results=[],  # Would be populated during execution
        )
    
    def reset_metrics(self) -> None:
        """Reset all chain metrics."""
        for step_id in self.step_metrics:
            self.step_metrics[step_id] = StepMetrics(step_id=step_id)
    
    def validate_dependencies(self) -> List[str]:
        """Validate step dependencies."""
        issues = []
        step_ids = {step.step_id for step in self.steps}
        
        for step in self.steps:
            for dependency in step.depends_on:
                if dependency not in step_ids:
                    issues.append(f"Step {step.step_id} depends on non-existent step: {dependency}")
        
        # Check for circular dependencies
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = self.get_step(step_id)
            if step:
                for dep in step.depends_on:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        for step in self.steps:
            if step.step_id not in visited:
                if has_cycle(step.step_id):
                    issues.append(f"Circular dependency detected involving step: {step.step_id}")
        
        return issues
    
    def validate_structure(self) -> List[str]:
        """Validate the basic structure of the chain."""
        issues = []
        
        if not self.steps:
            issues.append("Chain has no steps")
        
        # Validate each step
        for step in self.steps:
            if not step.step_id:
                issues.append("Step has no ID")
            
            if step.step_type == StepType.AGENT_EXECUTION and not step.agent:
                issues.append(f"Agent execution step {step.step_id} has no agent specified")
        
        # Validate dependencies
        issues.extend(self.validate_dependencies())
        
        return issues
    
    def __str__(self) -> str:
        return f"{self.chain_type.value}:{self.chain_id}"
    
    def __repr__(self) -> str:
        return f"Chain({self.chain_id}, type={self.chain_type.value}, steps={len(self.steps)})"


class SequentialChain(BaseChain):
    """Sequential chain implementation."""
    
    @property
    def chain_type(self) -> ChainType:
        return ChainType.SEQUENTIAL
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute steps sequentially."""
        import time
        
        start_time = time.time()
        self.status = ChainStatus.RUNNING
        
        # Initialize chain
        await self.initialize()
        
        # Execute each step in order
        for step in self.steps:
            try:
                # Check dependencies
                if not self._check_dependencies(step, context):
                    context[f"{step.step_id}_skipped"] = True
                    continue
                
                # Execute step
                step_result = await self._execute_step(step, context)
                
                # Update context with step results
                context.update(step_result.output)
                
                # Update metrics
                self.step_metrics[step.step_id].update_metrics(step_result)
                
                # Check if we should continue on failure
                if step_result.status == StepStatus.FAILED and not self.config.continue_on_step_failure:
                    self.status = ChainStatus.FAILED
                    break
                    
            except Exception as e:
                # Handle step execution error
                error_result = StepResult(
                    step_id=step.step_id,
                    status=StepStatus.FAILED,
                    error=str(e),
                    execution_time=0.0,
                )
                self.step_metrics[step.step_id].update_metrics(error_result)
                
                if not self.config.continue_on_step_failure:
                    self.status = ChainStatus.FAILED
                    context["error"] = str(e)
                    break
        
        # Update final status
        if self.status != ChainStatus.FAILED:
            self.status = ChainStatus.COMPLETED
        
        # Add execution summary
        context["chain_execution"] = {
            "chain_id": self.chain_id,
            "status": self.status.value,
            "execution_time": time.time() - start_time,
            "steps_executed": len(self.steps),
        }
        
        return context
    
    def _check_dependencies(self, step: ChainStep, context: Dict[str, Any]) -> bool:
        """Check if step dependencies are satisfied."""
        for dependency in step.depends_on:
            if dependency not in context:
                return False
        return True
    
    async def _execute_step(self, step: ChainStep, context: Dict[str, Any]) -> StepResult:
        """Execute a single step (placeholder implementation)."""
        import time
        
        start_time = time.time()
        
        try:
            # This would be replaced with actual step execution logic
            # For now, simulate execution
            await asyncio.sleep(0.1)  # Simulate work
            
            output = {
                f"{step.step_id}_result": f"Result of {step.step_id}",
                "step_completed": True,
            }
            
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                output=output,
                execution_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time(),
            )
            
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time(),
            )
    
    def validate(self) -> List[str]:
        """Validate sequential chain."""
        issues = self.validate_structure()
        
        # Sequential chains shouldn't have parallel groups
        for step in self.steps:
            if step.parallel_group:
                issues.append(f"Sequential chain step {step.step_id} has parallel_group")
        
        return issues


# Import for async sleep
import asyncio
