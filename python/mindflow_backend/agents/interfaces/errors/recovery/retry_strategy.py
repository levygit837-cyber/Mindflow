"""Retry strategy interface.

Defines contracts for retry mechanisms including backoff strategies,
retry conditions, and retry execution monitoring.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, List, Union, Callable
from abc import abstractmethod
from enum import Enum

from mindflow_backend.schemas.errors import ErrorSchema, ErrorCategory


class BackoffStrategy(str, Enum):
    """Backoff strategy types."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"
    CUSTOM = "custom"


@runtime_checkable
class RetryStrategyContract(Protocol):
    """Contract for retry strategy implementation.
    
    Provides configurable retry mechanisms with different backoff strategies,
    retry conditions, and execution monitoring.
    """

    @abstractmethod
    async def execute_with_retry(
        self,
        operation: Callable,
        *,
        max_attempts: int = 3,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        retry_on: Optional[List[Exception]] = None,
        retry_condition: Optional[Callable[[Exception], bool]] = None,
        jitter: bool = True,
        timeout: Optional[float] = None,
        **operation_kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute an operation with retry logic.
        
        Args:
            operation: The operation to execute
            max_attempts: Maximum number of retry attempts
            backoff_strategy: Strategy for calculating delay between retries
            base_delay: Base delay for backoff calculation
            max_delay: Maximum delay between retries
            retry_on: List of exception types to retry on
            retry_condition: Custom condition for retrying
            jitter: Whether to add random jitter to delays
            timeout: Total timeout for all attempts
            **operation_kwargs: Arguments to pass to operation
            
        Returns:
            Execution result with retry information
        """
        ...

    @abstractmethod
    def should_retry(
        self,
        exception: Exception,
        attempt: int,
        max_attempts: int,
        *,
        retry_on: Optional[List[Exception]] = None,
        retry_condition: Optional[Callable[[Exception], bool]] = None,
    ) -> bool:
        """Determine if an operation should be retried.
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number
            max_attempts: Maximum allowed attempts
            retry_on: List of retryable exception types
            retry_condition: Custom retry condition
            
        Returns:
            True if operation should be retried
        """
        ...

    @abstractmethod
    def calculate_delay(
        self,
        attempt: int,
        *,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        multiplier: float = 2.0,
    ) -> float:
        """Calculate delay before next retry attempt.
        
        Args:
            attempt: Current attempt number
            backoff_strategy: Strategy for delay calculation
            base_delay: Base delay value
            max_delay: Maximum allowed delay
            jitter: Whether to add random jitter
            multiplier: Multiplier for exponential/fibonacci strategies
            
        Returns:
            Delay in seconds before next retry
        """
        ...

    @abstractmethod
    def get_retry_statistics(
        self,
        operation_name: Optional[str] = None,
        time_range: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get retry statistics for monitoring.
        
        Args:
            operation_name: Specific operation to get stats for
            time_range: Time range for statistics (1h, 24h, 7d, etc.)
            
        Returns:
            Retry statistics
        """
        ...

    @abstractmethod
    def register_retry_condition(
        self,
        name: str,
        condition: Callable[[Exception], bool],
        *,
        priority: int = 0,
        enabled: bool = True,
    ) -> None:
        """Register a custom retry condition.
        
        Args:
            name: Condition name
            condition: Condition function
            priority: Condition priority
            enabled: Whether condition is enabled
        """
        ...

    @abstractmethod
    def register_backoff_strategy(
        self,
        name: str,
        strategy: Callable[[int, float, float], float],
        *,
        description: Optional[str] = None,
    ) -> None:
        """Register a custom backoff strategy.
        
        Args:
            name: Strategy name
            strategy: Strategy function
            description: Strategy description
        """
        ...

    @abstractmethod
    async def get_retry_history(
        self,
        operation_name: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get history of retry operations.
        
        Args:
            operation_name: Specific operation to filter by
            error_type: Specific error type to filter by
            limit: Maximum number of records
            
        Returns:
            List of retry operation records
        """
        ...

    @abstractmethod
    def analyze_retry_effectiveness(
        self,
        operation_name: Optional[str] = None,
        backoff_strategy: Optional[BackoffStrategy] = None,
        time_range: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze retry strategy effectiveness.
        
        Args:
            operation_name: Specific operation to analyze
            backoff_strategy: Specific backoff strategy to analyze
            time_range: Time range for analysis
            
        Returns:
            Retry effectiveness analysis
        """
        ...

    # Retry-specific convenience methods
    
    def create_retry_config(
        self,
        max_attempts: int = 3,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a retry configuration dictionary.
        
        Args:
            max_attempts: Maximum retry attempts
            backoff_strategy: Backoff strategy type
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add jitter
            timeout: Total timeout
            
        Returns:
            Retry configuration dictionary
        """
        return {
            "max_attempts": max_attempts,
            "backoff_strategy": backoff_strategy,
            "base_delay": base_delay,
            "max_delay": max_delay,
            "jitter": jitter,
            "timeout": timeout,
            "multiplier": 2.0,  # Default for exponential
        }

    def simulate_retry_strategy(
        self,
        backoff_strategy: BackoffStrategy,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = False,
    ) -> Dict[str, Any]:
        """Simulate retry strategy delays.
        
        Args:
            backoff_strategy: Strategy to simulate
            max_attempts: Number of attempts to simulate
            base_delay: Base delay
            max_delay: Maximum delay
            jitter: Whether to simulate jitter
            
        Returns:
            Simulation results with delays
        """
        delays = []
        total_delay = 0.0
        
        for attempt in range(1, max_attempts + 1):
            delay = self.calculate_delay(
                attempt=attempt,
                backoff_strategy=backoff_strategy,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter,
            )
            delays.append(delay)
            total_delay += delay
        
        return {
            "strategy": backoff_strategy.value,
            "max_attempts": max_attempts,
            "base_delay": base_delay,
            "max_delay": max_delay,
            "jitter": jitter,
            "delays": delays,
            "total_delay": total_delay,
            "average_delay": total_delay / len(delays),
            "min_delay": min(delays),
            "max_calculated_delay": max(delays),
        }

    def get_optimal_retry_config(
        self,
        operation_name: str,
        error_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get optimal retry configuration based on historical data.
        
        Args:
            operation_name: Operation name to optimize for
            error_type: Specific error type to optimize for
            
        Returns:
            Optimal retry configuration
        """
        # Default implementation - subclasses should override with actual data
        return {
            "operation": operation_name,
            "error_type": error_type,
            "optimal_config": self.create_retry_config(
                max_attempts=3,
                backoff_strategy=BackoffStrategy.EXPONENTIAL,
                base_delay=1.0,
                max_delay=30.0,
                jitter=True,
            ),
            "success_rate_estimate": 0.85,
            "confidence": 0.7,
            "based_on_operations": 100,  # Would be actual count
        }

    def validate_retry_config(
        self,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate retry configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation results
        """
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["max_attempts", "backoff_strategy", "base_delay"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate values
        if "max_attempts" in config:
            max_attempts = config["max_attempts"]
            if not isinstance(max_attempts, int) or max_attempts < 1:
                errors.append("max_attempts must be a positive integer")
            elif max_attempts > 10:
                warnings.append("max_attempts > 10 may be excessive")
        
        if "base_delay" in config:
            base_delay = config["base_delay"]
            if not isinstance(base_delay, (int, float)) or base_delay < 0:
                errors.append("base_delay must be a positive number")
            elif base_delay > 30:
                warnings.append("base_delay > 30 seconds may be too long")
        
        if "max_delay" in config and "base_delay" in config:
            base_delay = config["base_delay"]
            max_delay = config["max_delay"]
            if max_delay < base_delay:
                errors.append("max_delay must be >= base_delay")
        
        if "backoff_strategy" in config:
            strategy = config["backoff_strategy"]
            if not isinstance(strategy, BackoffStrategy):
                try:
                    BackoffStrategy(strategy)
                except ValueError:
                    errors.append(f"Invalid backoff_strategy: {strategy}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "config": config,
        }

    def create_retry_decorator(
        self,
        config: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Create a retry decorator from configuration.
        
        Args:
            config: Retry configuration
            
        Returns:
            Retry decorator function
        """
        if config is None:
            config = self.create_retry_config()
        
        def retry_decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                # Merge config with operation kwargs
                merged_kwargs = {**config, **kwargs}
                return await self.execute_with_retry(
                    func,
                    *args,
                    **merged_kwargs
                )
            return wrapper
        
        return retry_decorator
