"""Skill executor implementation."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from mindflow_backend.interfaces.skills.executor import (
    AsyncSkillExecutorInterface,
    BatchSkillExecutorInterface,
    SkillExecutionManagerInterface,
    SkillExecutorInterface,
)
from mindflow_backend.interfaces.skills.registry import SkillRegistryInterface
from mindflow_backend.schemas.skills.base import SkillInput
from mindflow_backend.schemas.skills.execution import (
    ExecutionContext,
    ExecutionMetrics,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)


class SkillExecutor(SkillExecutorInterface, AsyncSkillExecutorInterface, BatchSkillExecutorInterface):
    """Implementation of skill executor."""
    
    def __init__(self, registry: SkillRegistryInterface):
        self._registry = registry
        self._running_executions: dict[str, asyncio.Task] = {}
        self._execution_results: dict[str, ExecutionResult] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the executor."""
        self._initialized = True
    
    async def shutdown(self):
        """Shutdown the executor."""
        # Cancel all running executions
        for execution_id, task in self._running_executions.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._running_executions.clear()
        self._execution_results.clear()
        self._initialized = False
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Execute a skill with given context."""
        if not self._initialized:
            raise RuntimeError("Executor not initialized")
        
        execution_id = context.execution_id
        start_time = datetime.now()
        
        try:
            # Get the skill
            skill = await self._registry.get_skill_by_name(context.skill_name)
            if not skill:
                raise ValueError(f"Skill not found: {context.skill_name}")
            
            # Validate execution context
            if not skill.validate_execution_context(context.environment):
                raise ValueError("Invalid execution context")
            
            # Validate permissions
            if not skill.validate_permissions(context.permissions):
                raise ValueError("Insufficient permissions")
            
            # Create execution metrics
            metrics = ExecutionMetrics(start_time=start_time)
            
            # Execute the skill
            output = await skill.execute(context.input_data)
            
            # Create execution result
            end_time = datetime.now()
            metrics.end_time = end_time
            
            result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED if output.success else ExecutionStatus.FAILED,
                output=output,
                error=output.error if not output.success else None,
                metrics=metrics,
                logs=[f"Started execution at {start_time}", f"Completed execution at {end_time}"]
            )
            
            # Store result
            self._execution_results[execution_id] = result
            
            return result
            
        except Exception as e:
            # Create error result
            end_time = datetime.now()
            metrics = ExecutionMetrics(start_time=start_time, end_time=end_time)
            
            result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                output=None,
                error=str(e),
                metrics=metrics,
                logs=[f"Execution failed: {str(e)}"]
            )
            
            self._execution_results[execution_id] = result
            return result
    
    def can_execute(self, skill_name: str) -> bool:
        """Check if executor can handle the skill."""
        # For now, assume we can execute any registered skill
        return True
    
    def get_supported_skills(self) -> list[str]:
        """Get list of supported skills."""
        # This would typically query the registry
        return []
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an ongoing execution."""
        if execution_id in self._running_executions:
            task = self._running_executions[execution_id]
            task.cancel()
            try:
                await task
                del self._running_executions[execution_id]
                return True
            except asyncio.CancelledError:
                del self._running_executions[execution_id]
                return True
        return False
    
    async def execute_stream(self, context: ExecutionContext) -> AsyncGenerator[dict[str, Any], None]:
        """Execute skill with streaming output."""
        # For now, implement as regular execution with single result
        result = await self.execute(context)
        
        yield {
            "type": "progress",
            "execution_id": context.execution_id,
            "progress": 100.0,
            "message": "Execution completed"
        }
        
        yield {
            "type": "result",
            "execution_id": context.execution_id,
            "result": result.dict()
        }
    
    async def execute_with_timeout(
        self, 
        context: ExecutionContext, 
        timeout_seconds: int
    ) -> ExecutionResult:
        """Execute skill with timeout."""
        try:
            return await asyncio.wait_for(
                self.execute(context),
                timeout=timeout_seconds
            )
        except TimeoutError:
            # Create timeout result
            start_time = datetime.now()
            metrics = ExecutionMetrics(start_time=start_time)
            
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.TIMEOUT,
                output=None,
                error=f"Execution timed out after {timeout_seconds} seconds",
                metrics=metrics,
                logs=[f"Execution timed out after {timeout_seconds} seconds"]
            )
    
    async def execute_with_retry(
        self, 
        context: ExecutionContext, 
        max_retries: int = 3
    ) -> ExecutionResult:
        """Execute skill with retry logic."""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.execute(context)
                
                # If successful, return result
                if result.status == ExecutionStatus.COMPLETED:
                    if attempt > 0:
                        result.logs.append(f"Success on attempt {attempt + 1}")
                    return result
                
                last_error = result.error
                
            except Exception as e:
                last_error = str(e)
            
            # Don't retry on the last attempt
            if attempt < max_retries:
                await asyncio.sleep(1 * (2 ** attempt))  # Exponential backoff
        
        # All attempts failed
        start_time = datetime.now()
        metrics = ExecutionMetrics(start_time=start_time)
        
        return ExecutionResult(
            execution_id=context.execution_id,
            status=ExecutionStatus.FAILED,
            output=None,
            error=f"All {max_retries + 1} attempts failed. Last error: {last_error}",
            metrics=metrics,
            logs=[f"Failed after {max_retries + 1} attempts"]
        )
    
    async def execute_batch(self, requests: list[ExecutionRequest]) -> list[ExecutionResult]:
        """Execute multiple skills in batch."""
        results = []
        
        for request in requests:
            context = ExecutionContext(
                execution_id=str(uuid.uuid4()),
                skill_name=request.skill_name,
                input_data=SkillInput(
                    data=request.input_data,
                    parameters=request.parameters,
                    context=request.context
                )
            )
            
            result = await self.execute(context)
            results.append(result)
        
        return results
    
    async def execute_parallel(
        self, 
        requests: list[ExecutionRequest],
        max_concurrent: int | None = None
    ) -> list[ExecutionResult]:
        """Execute multiple skills in parallel."""
        if max_concurrent is None:
            max_concurrent = len(requests)
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(request: ExecutionRequest) -> ExecutionResult:
            async with semaphore:
                context = ExecutionContext(
                    execution_id=str(uuid.uuid4()),
                    skill_name=request.skill_name,
                    input_data=SkillInput(
                        data=request.input_data,
                        parameters=request.parameters,
                        context=request.context
                    )
                )
                return await self.execute(context)
        
        tasks = [execute_with_semaphore(request) for request in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def execute_sequential(
        self, 
        requests: list[ExecutionRequest],
        fail_fast: bool = False
    ) -> list[ExecutionResult]:
        """Execute multiple skills sequentially."""
        results = []
        
        for request in requests:
            context = ExecutionContext(
                execution_id=str(uuid.uuid4()),
                skill_name=request.skill_name,
                input_data=SkillInput(
                    data=request.input_data,
                    parameters=request.parameters,
                    context=request.context
                )
            )
            
            result = await self.execute(context)
            results.append(result)
            
            # Stop on first failure if fail_fast is True
            if fail_fast and result.status == ExecutionStatus.FAILED:
                break
        
        return results


class SkillExecutionManager(SkillExecutionManagerInterface):
    """Implementation of skill execution manager."""
    
    def __init__(self, executor: SkillExecutorInterface):
        self._executor = executor
        self._execution_queue = asyncio.Queue()
        self._worker_task = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the execution manager."""
        if self._initialized:
            return
        
        self._worker_task = asyncio.create_task(self._worker())
        self._initialized = True
    
    async def shutdown(self):
        """Shutdown the execution manager."""
        if not self._initialized:
            return
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        self._initialized = False
    
    async def _worker(self):
        """Worker task for processing execution queue."""
        while True:
            try:
                request = await self._execution_queue.get()
                # Process request (implementation would go here)
                self._execution_queue.task_done()
            except asyncio.CancelledError:
                break
    
    async def submit_execution(self, request: ExecutionRequest) -> str:
        """Submit an execution request."""
        execution_id = str(uuid.uuid4())
        
        # Create context and submit to executor
        context = ExecutionContext(
            execution_id=execution_id,
            skill_name=request.skill_name,
            input_data=SkillInput(
                data=request.input_data,
                parameters=request.parameters,
                context=request.context
            )
        )
        
        # Submit to executor (in a real implementation, this would be queued)
        asyncio.create_task(self._executor.execute(context))
        
        return execution_id
    
    async def get_execution_status(self, execution_id: str) -> ExecutionStatus:
        """Get status of an execution."""
        # This would typically check the execution store
        return ExecutionStatus.PENDING
    
    async def get_execution_result(self, execution_id: str) -> ExecutionResult | None:
        """Get result of an execution."""
        # This would typically check the execution store
        return None
    
    async def list_executions(
        self,
        skill_name: str | None = None,
        status: ExecutionStatus | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """List executions with optional filtering."""
        # This would typically query the execution store
        return []
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        return await self._executor.cancel_execution(execution_id)
