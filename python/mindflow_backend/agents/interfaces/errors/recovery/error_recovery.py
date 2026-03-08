"""Error recovery interface.

Defines contracts for automated error recovery processes, including
recovery strategy selection, execution, and monitoring.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, List, Union, Callable
from abc import abstractmethod

from mindflow_backend.schemas.errors import ErrorSchema, ErrorCategory


@runtime_checkable
class ErrorRecoveryContract(Protocol):
    """Contract for error recovery strategies and execution.
    
    Provides automated recovery capabilities for different types of errors,
    including strategy selection, execution monitoring, and recovery tracking.
    """

    @abstractmethod
    async def recover_from_error(
        self,
        error_schema: ErrorSchema,
        *,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        max_attempts: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Attempt to recover from an error automatically.
        
        Args:
            error_schema: The error to recover from
            operation: Operation that was being performed
            context: Additional recovery context
            max_attempts: Maximum recovery attempts
            timeout: Recovery operation timeout
            
        Returns:
            Recovery result with status and details
        """
        ...

    @abstractmethod
    def get_recovery_strategy(
        self,
        error_schema: ErrorSchema,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Get the appropriate recovery strategy for an error.
        
        Args:
            error_schema: The error to get strategy for
            context: Additional context for strategy selection
            
        Returns:
            Recovery strategy name or None if not recoverable
        """
        ...

    @abstractmethod
    def is_recoverable(
        self,
        error_schema: ErrorSchema,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Determine if an error is recoverable.
        
        Args:
            error_schema: The error to evaluate
            context: Additional context for decision
            
        Returns:
            True if the error is recoverable
        """
        ...

    @abstractmethod
    async def execute_recovery_strategy(
        self,
        strategy_name: str,
        error_schema: ErrorSchema,
        *,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **strategy_params: Any,
    ) -> Dict[str, Any]:
        """Execute a specific recovery strategy.
        
        Args:
            strategy_name: Name of recovery strategy to execute
            error_schema: The error to recover from
            operation: Operation that was being performed
            context: Additional recovery context
            **strategy_params: Strategy-specific parameters
            
        Returns:
            Recovery execution result
        """
        ...

    @abstractmethod
    def register_recovery_strategy(
        self,
        name: str,
        strategy: Callable,
        *,
        error_categories: Optional[List[ErrorCategory]] = None,
        error_types: Optional[List[str]] = None,
        priority: int = 0,
        enabled: bool = True,
    ) -> None:
        """Register a custom recovery strategy.
        
        Args:
            name: Strategy name
            strategy: Strategy function/implementation
            error_categories: Categories this strategy handles
            error_types: Specific error types this strategy handles
            priority: Strategy priority (higher = more priority)
            enabled: Whether strategy is enabled
        """
        ...

    @abstractmethod
    async def monitor_recovery_progress(
        self,
        recovery_id: str,
    ) -> Dict[str, Any]:
        """Monitor the progress of an ongoing recovery operation.
        
        Args:
            recovery_id: Recovery operation identifier
            
        Returns:
            Recovery progress information
        """
        ...

    @abstractmethod
    def get_recovery_history(
        self,
        error_type: Optional[str] = None,
        time_range: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get history of recovery operations.
        
        Args:
            error_type: Specific error type to filter by
            time_range: Time range for history (1h, 24h, 7d, etc.)
            limit: Maximum number of records to return
            
        Returns:
            List of recovery operation records
        """
        ...

    @abstractmethod
    def analyze_recovery_success_rate(
        self,
        strategy_name: Optional[str] = None,
        error_category: Optional[ErrorCategory] = None,
        time_range: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze recovery success rates.
        
        Args:
            strategy_name: Specific strategy to analyze
            error_category: Specific error category to analyze
            time_range: Time range for analysis
            
        Returns:
            Recovery success rate analysis
        """
        ...

    @abstractmethod
    async def cancel_recovery(
        self,
        recovery_id: str,
        *,
        reason: Optional[str] = None,
    ) -> bool:
        """Cancel an ongoing recovery operation.
        
        Args:
            recovery_id: Recovery operation identifier
            reason: Reason for cancellation
            
        Returns:
            True if recovery was successfully cancelled
        """
        ...

    @abstractmethod
    def get_recovery_recommendations(
        self,
        error_schema: ErrorSchema,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Get recommendations for manual recovery.
        
        Args:
            error_schema: The error to get recommendations for
            context: Additional context
            
        Returns:
            List of recovery recommendations
        """
        ...

    # Recovery-specific convenience methods
    
    def get_available_strategies(
        self,
        error_category: Optional[ErrorCategory] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Get list of available recovery strategies.
        
        Args:
            error_category: Filter by error category
            
        Returns:
            Available strategies with metadata
        """
        # Default implementation - subclasses should override
        return {
            "retry": {
                "name": "retry",
                "description": "Retry the failed operation",
                "categories": [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT],
                "enabled": True,
                "priority": 1,
            },
            "fallback": {
                "name": "fallback",
                "description": "Use fallback service/method",
                "categories": [ErrorCategory.INFRASTRUCTURE, ErrorCategory.RESOURCE],
                "enabled": True,
                "priority": 2,
            },
            "circuit_reset": {
                "name": "circuit_reset",
                "description": "Reset circuit breaker",
                "categories": [ErrorCategory.INFRASTRUCTURE],
                "enabled": True,
                "priority": 3,
            },
        }

    def create_recovery_plan(
        self,
        error_schema: ErrorSchema,
        *,
        context: Optional[Dict[str, Any]] = None,
        max_strategies: int = 3,
    ) -> Dict[str, Any]:
        """Create a recovery plan for an error.
        
        Args:
            error_schema: The error to create plan for
            context: Additional context
            max_strategies: Maximum strategies to include
            
        Returns:
            Recovery plan with ordered strategies
        """
        # Default implementation - subclasses should override
        strategies = self.get_available_strategies(error_schema.category)
        
        # Sort by priority and limit
        sorted_strategies = sorted(
            strategies.items(),
            key=lambda x: x[1].get("priority", 0),
            reverse=True
        )[:max_strategies]
        
        return {
            "error_id": error_schema.error_id,
            "error_type": error_schema.error_type,
            "category": error_schema.category.value,
            "strategies": [
                {
                    "name": name,
                    "description": info.get("description"),
                    "priority": info.get("priority", 0),
                    "estimated_success_rate": 0.0,  # Would be calculated from history
                }
                for name, info in sorted_strategies
            ],
            "estimated_recovery_time": 0.0,  # Would be calculated from history
            "manual_intervention_required": False,
        }

    def simulate_recovery(
        self,
        error_schema: ErrorSchema,
        strategy_name: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        iterations: int = 100,
    ) -> Dict[str, Any]:
        """Simulate recovery strategy execution.
        
        Args:
            error_schema: The error to simulate recovery for
            strategy_name: Recovery strategy to simulate
            context: Additional context
            iterations: Number of simulation iterations
            
        Returns:
            Simulation results with success rates and timing
        """
        # Default implementation - subclasses should override
        import random
        
        success_count = 0
        total_time = 0.0
        
        for _ in range(iterations):
            # Simulate recovery attempt
            success = random.random() > 0.3  # 70% success rate
            time_taken = random.uniform(0.1, 2.0)  # 0.1-2.0 seconds
            
            if success:
                success_count += 1
            total_time += time_taken
        
        success_rate = success_count / iterations
        average_time = total_time / iterations
        
        return {
            "strategy": strategy_name,
            "error_type": error_schema.error_type,
            "iterations": iterations,
            "success_count": success_count,
            "success_rate": success_rate,
            "average_recovery_time": average_time,
            "min_time": 0.1,  # Would be calculated from simulation
            "max_time": 2.0,  # Would be calculated from simulation
            "recommendation": "use" if success_rate > 0.5 else "avoid",
        }
