"""Executor interfaces for Skills system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from datetime import datetime

from mindflow_backend.interfaces.core import BaseComponentInterface
from mindflow_backend.schemas.skills.base import SkillInput, SkillOutput
from mindflow_backend.schemas.skills.execution import (
    ExecutionContext,
    ExecutionResult,
    ExecutionRequest,
    BatchExecutionRequest,
    ExecutionStatus
)


class SkillExecutorInterface(BaseComponentInterface):
    """Interface for skill execution."""
    
    @abstractmethod
    async def execute(
        self, 
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute a skill with given context.
        
        Args:
            context: Execution context containing all necessary data
            
        Returns:
            ExecutionResult: Result of execution
            
        Raises:
            SkillExecutionError: If execution fails
        """
        pass
    
    @abstractmethod
    def can_execute(self, skill_name: str) -> bool:
        """Check if executor can handle the skill.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            bool: True if skill can be executed
        """
        pass
    
    @abstractmethod
    def get_supported_skills(self) -> List[str]:
        """Get list of supported skills.
        
        Returns:
            List[str]: List of skill names
        """
        pass
    
    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an ongoing execution.
        
        Args:
            execution_id: ID of execution to cancel
            
        Returns:
            bool: True if cancellation was successful
        """
        pass


class AsyncSkillExecutorInterface(SkillExecutorInterface):
    """Interface for asynchronous skill execution."""
    
    @abstractmethod
    async def execute_stream(
        self, 
        context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute skill with streaming output.
        
        Args:
            context: Execution context
            
        Yields:
            Dict[str, Any]: Partial execution results
        """
        pass
    
    @abstractmethod
    async def execute_with_timeout(
        self, 
        context: ExecutionContext, 
        timeout_seconds: int
    ) -> ExecutionResult:
        """Execute skill with timeout.
        
        Args:
            context: Execution context
            timeout_seconds: Maximum execution time
            
        Returns:
            ExecutionResult: Result of execution
            
        Raises:
            TimeoutError: If execution times out
        """
        pass
    
    @abstractmethod
    async def execute_with_retry(
        self, 
        context: ExecutionContext, 
        max_retries: int = 3
    ) -> ExecutionResult:
        """Execute skill with retry logic.
        
        Args:
            context: Execution context
            max_retries: Maximum number of retries
            
        Returns:
            ExecutionResult: Result of execution
        """
        pass


class BatchSkillExecutorInterface(SkillExecutorInterface):
    """Interface for batch skill execution."""
    
    @abstractmethod
    async def execute_batch(
        self, 
        requests: List[ExecutionRequest]
    ) -> List[ExecutionResult]:
        """Execute multiple skills in batch.
        
        Args:
            requests: List of execution requests
            
        Returns:
            List[ExecutionResult]: Results for all executions
        """
        pass
    
    @abstractmethod
    async def execute_parallel(
        self, 
        requests: List[ExecutionRequest],
        max_concurrent: Optional[int] = None
    ) -> List[ExecutionResult]:
        """Execute multiple skills in parallel.
        
        Args:
            requests: List of execution requests
            max_concurrent: Maximum concurrent executions
            
        Returns:
            List[ExecutionResult]: Results for all executions
        """
        pass
    
    @abstractmethod
    async def execute_sequential(
        self, 
        requests: List[ExecutionRequest],
        fail_fast: bool = False
    ) -> List[ExecutionResult]:
        """Execute multiple skills sequentially.
        
        Args:
            requests: List of execution requests
            fail_fast: Stop on first failure
            
        Returns:
            List[ExecutionResult]: Results for all executions
        """
        pass


class SkillExecutionManagerInterface(BaseComponentInterface):
    """Interface for managing skill executions."""
    
    @abstractmethod
    async def submit_execution(
        self, 
        request: ExecutionRequest
    ) -> str:
        """Submit an execution request.
        
        Args:
            request: Execution request
            
        Returns:
            str: Execution ID
        """
        pass
    
    @abstractmethod
    async def get_execution_status(
        self, 
        execution_id: str
    ) -> ExecutionStatus:
        """Get status of an execution.
        
        Args:
            execution_id: ID of execution
            
        Returns:
            ExecutionStatus: Current status
        """
        pass
    
    @abstractmethod
    async def get_execution_result(
        self, 
        execution_id: str
    ) -> Optional[ExecutionResult]:
        """Get result of an execution.
        
        Args:
            execution_id: ID of execution
            
        Returns:
            Optional[ExecutionResult]: Result if available
        """
        pass
    
    @abstractmethod
    async def list_executions(
        self,
        skill_name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List executions with optional filtering.
        
        Args:
            skill_name: Filter by skill name
            status: Filter by status
            limit: Maximum results to return
            offset: Results offset
            
        Returns:
            List[Dict[str, Any]]: List of execution information
        """
        pass
    
    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution.
        
        Args:
            execution_id: ID of execution to cancel
            
        Returns:
            bool: True if cancellation was successful
        """
        pass


class SkillExecutionMonitorInterface(BaseComponentInterface):
    """Interface for monitoring skill executions."""
    
    @abstractmethod
    async def track_execution(
        self, 
        execution_id: str,
        context: ExecutionContext
    ) -> None:
        """Track execution start.
        
        Args:
            execution_id: ID of execution
            context: Execution context
        """
        pass
    
    @abstractmethod
    async def update_execution_progress(
        self, 
        execution_id: str,
        progress: float,
        message: Optional[str] = None
    ) -> None:
        """Update execution progress.
        
        Args:
            execution_id: ID of execution
            progress: Progress percentage (0.0 to 1.0)
            message: Optional progress message
        """
        pass
    
    @abstractmethod
    async def complete_execution(
        self, 
        execution_id: str,
        result: ExecutionResult
    ) -> None:
        """Mark execution as completed.
        
        Args:
            execution_id: ID of execution
            result: Final execution result
        """
        pass
    
    @abstractmethod
    async def get_execution_metrics(
        self,
        skill_name: Optional[str] = None,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """Get execution metrics.
        
        Args:
            skill_name: Filter by skill name
            time_range: Filter by time range
            
        Returns:
            Dict[str, Any]: Execution metrics
        """
        pass
