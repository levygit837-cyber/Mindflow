"""
MCP Error Handlers

Handlers for processing MCP errors and error recovery.
Provides error classification, logging, and recovery strategies.
"""

import asyncio
import logging
from enum import Enum
from typing import Any

from mindflow_backend.schemas.mcp.base import MCPError, MCPErrorCode, MCPMessage


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    NETWORK = "network"
    PROTOCOL = "protocol"
    VALIDATION = "validation"
    EXECUTION = "execution"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INTERNAL = "internal"


class ErrorInfo:
    """Information about an error."""
    
    def __init__(
        self,
        error: Exception,
        message: MCPMessage | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        context: dict[str, Any] | None = None,
        recoverable: bool = True,
        retry_after: float | None = None
    ):
        """
        Initialize error information.
        
        Args:
            error: The exception that occurred
            message: The MCP message being processed (if any)
            severity: Error severity level
            category: Error category
            context: Additional context information
            recoverable: Whether the error is recoverable
            retry_after: Suggested retry delay in seconds
        """
        self.error = error
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.timestamp = asyncio.get_event_loop().time()
        self.attempt_count = 1


class ErrorProcessor:
    """
    Base class for error processors.
    
    Error processors analyze errors and determine appropriate
    handling strategies and recovery actions.
    """
    
    def __init__(self):
        """Initialize the error processor."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    async def process_error(self, error_info: ErrorInfo) -> bool:
        """
        Process an error and determine if it can be recovered.
        
        Args:
            error_info: Information about the error
            
        Returns:
            bool: True if the error can be recovered, False otherwise
        """
        try:
            # Log the error
            self._log_error(error_info)
            
            # Determine recovery strategy
            recovery_action = await self._determine_recovery_action(error_info)
            
            # Execute recovery if possible
            if recovery_action and error_info.recoverable:
                return await self._execute_recovery(error_info, recovery_action)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in error processor: {e}")
            return False
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """
        Log the error with appropriate level.
        
        Args:
            error_info: Information about the error
        """
        log_message = f"Error: {error_info.error}"
        
        if error_info.message:
            log_message += f" (Message ID: {error_info.message.id})"
        
        if error_info.context:
            log_message += f" (Context: {error_info.context})"
        
        # Choose log level based on severity
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    async def _determine_recovery_action(self, error_info: ErrorInfo) -> str | None:
        """
        Determine the appropriate recovery action.
        
        Args:
            error_info: Information about the error
            
        Returns:
            Optional[str]: Recovery action name
        """
        # This should be implemented by subclasses
        return None
    
    async def _execute_recovery(self, error_info: ErrorInfo, action: str) -> bool:
        """
        Execute a recovery action.
        
        Args:
            error_info: Information about the error
            action: Recovery action to execute
            
        Returns:
            bool: True if recovery was successful
        """
        # This should be implemented by subclasses
        return False


class MCPErrorHandler:
    """
    Main error handler for MCP operations.
    
    This handler classifies errors, logs them, and attempts recovery
    using registered error processors.
    """
    
    def __init__(self):
        """Initialize the MCP error handler."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._processors: list[ErrorProcessor] = []
        self._error_history: list[ErrorInfo] = []
        self._max_history = 1000
    
    def add_processor(self, processor: ErrorProcessor) -> None:
        """
        Add an error processor.
        
        Args:
            processor: The error processor to add
        """
        self._processors.append(processor)
        self.logger.debug(f"Added error processor: {processor.__class__.__name__}")
    
    def remove_processor(self, processor: ErrorProcessor) -> None:
        """
        Remove an error processor.
        
        Args:
            processor: The error processor to remove
        """
        if processor in self._processors:
            self._processors.remove(processor)
            self.logger.debug(f"Removed error processor: {processor.__class__.__name__}")
    
    async def handle_error(
        self,
        error: Exception,
        message: MCPMessage | None = None,
        context: dict[str, Any] | None = None
    ) -> bool:
        """
        Handle an error and attempt recovery.
        
        Args:
            error: The exception that occurred
            message: The MCP message being processed (if any)
            context: Additional context information
            
        Returns:
            bool: True if the error was handled/recovered, False otherwise
        """
        try:
            # Classify the error
            error_info = self._classify_error(error, message, context)
            
            # Store in history
            self._add_to_history(error_info)
            
            # Try each processor in order
            for processor in self._processors:
                try:
                    recovered = await processor.process_error(error_info)
                    if recovered:
                        self.logger.info(f"Error recovered by {processor.__class__.__name__}")
                        return True
                except Exception as e:
                    self.logger.error(f"Error processor {processor.__class__.__name__} failed: {e}")
            
            # No processor could recover the error
            self.logger.warning("No error processor could recover the error")
            return False
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")
            return False
    
    def _classify_error(
        self,
        error: Exception,
        message: MCPMessage | None = None,
        context: dict[str, Any] | None = None
    ) -> ErrorInfo:
        """
        Classify an error to determine severity and category.
        
        Args:
            error: The exception to classify
            message: The MCP message being processed (if any)
            context: Additional context information
            
        Returns:
            ErrorInfo: Classified error information
        """
        # Default classification
        severity = ErrorSeverity.MEDIUM
        category = ErrorCategory.INTERNAL
        recoverable = True
        retry_after = None
        
        # Classify based on error type
        if isinstance(error, ConnectionError):
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.HIGH
            retry_after = 5.0
        elif isinstance(error, TimeoutError):
            category = ErrorCategory.TIMEOUT
            severity = ErrorSeverity.MEDIUM
            retry_after = 2.0
        elif isinstance(error, ValueError):
            category = ErrorCategory.VALIDATION
            severity = ErrorSeverity.LOW
            recoverable = False
        elif isinstance(error, PermissionError):
            category = ErrorCategory.AUTHORIZATION
            severity = ErrorSeverity.HIGH
            recoverable = False
        
        # Check for MCP-specific errors
        if hasattr(error, 'code'):
            mcp_error = error
            if isinstance(mcp_error, MCPError):
                if mcp_error.code in [MCPErrorCode.SERVER_NOT_INITIALIZED]:
                    category = ErrorCategory.PROTOCOL
                    severity = ErrorSeverity.MEDIUM
                    retry_after = 1.0
                elif mcp_error.code in [MCPErrorCode.INVALID_PARAMS]:
                    category = ErrorCategory.VALIDATION
                    severity = ErrorSeverity.LOW
                    recoverable = False
                elif mcp_error.code in [MCPErrorCode.METHOD_NOT_FOUND]:
                    category = ErrorCategory.PROTOCOL
                    severity = ErrorSeverity.MEDIUM
                    recoverable = False
        
        return ErrorInfo(
            error=error,
            message=message,
            severity=severity,
            category=category,
            context=context,
            recoverable=recoverable,
            retry_after=retry_after
        )
    
    def _add_to_history(self, error_info: ErrorInfo) -> None:
        """
        Add error information to history.
        
        Args:
            error_info: Information about the error
        """
        self._error_history.append(error_info)
        
        # Trim history if it gets too large
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history:]
    
    def get_error_stats(self) -> dict[str, Any]:
        """
        Get error statistics.
        
        Returns:
            Dict[str, Any]: Error statistics
        """
        if not self._error_history:
            return {
                "total_errors": 0,
                "by_severity": {},
                "by_category": {},
                "recoverable_rate": 0.0
            }
        
        total_errors = len(self._error_history)
        by_severity = {}
        by_category = {}
        recoverable_count = 0
        
        for error_info in self._error_history:
            # Count by severity
            severity = error_info.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Count by category
            category = error_info.category.value
            by_category[category] = by_category.get(category, 0) + 1
            
            # Count recoverable
            if error_info.recoverable:
                recoverable_count += 1
        
        return {
            "total_errors": total_errors,
            "by_severity": by_severity,
            "by_category": by_category,
            "recoverable_rate": recoverable_count / total_errors if total_errors > 0 else 0.0
        }
    
    def get_recent_errors(self, limit: int = 10) -> list[ErrorInfo]:
        """
        Get recent errors from history.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List[ErrorInfo]: Recent errors
        """
        return self._error_history[-limit:]


class RetryProcessor(ErrorProcessor):
    """
    Error processor that implements retry logic.
    
    This processor attempts to recover from recoverable errors
    by retrying the operation with exponential backoff.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Initialize retry processor.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff
            max_delay: Maximum delay between retries
        """
        super().__init__()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def _determine_recovery_action(self, error_info: ErrorInfo) -> str | None:
        """Determine if retry is appropriate."""
        if not error_info.recoverable:
            return None
        
        if error_info.attempt_count > self.max_retries:
            return None
        
        return "retry"
    
    async def _execute_recovery(self, error_info: ErrorInfo, action: str) -> bool:
        """Execute retry with exponential backoff."""
        if action != "retry":
            return False
        
        # Calculate delay with exponential backoff
        delay = min(
            self.base_delay * (2 ** (error_info.attempt_count - 1)),
            self.max_delay
        )
        
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0, delay * 0.1)
        delay += jitter
        
        self.logger.info(f"Retrying operation after {delay:.2f}s (attempt {error_info.attempt_count})")
        
        # Wait before retry
        await asyncio.sleep(delay)
        
        # Increment attempt count
        error_info.attempt_count += 1
        
        return True  # Signal that retry should be attempted


class LoggingProcessor(ErrorProcessor):
    """
    Error processor that logs detailed error information.
    
    This processor provides comprehensive logging of errors
    including stack traces and context information.
    """
    
    def __init__(self, include_stack_trace: bool = True):
        """
        Initialize logging processor.
        
        Args:
            include_stack_trace: Whether to include stack traces in logs
        """
        super().__init__()
        self.include_stack_trace = include_stack_trace
    
    async def _determine_recovery_action(self, error_info: ErrorInfo) -> str | None:
        """This processor only logs, doesn't recover."""
        return None
    
    async def _execute_recovery(self, error_info: ErrorInfo, action: str) -> bool:
        """This processor only logs, doesn't recover."""
        return False
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log detailed error information."""
        super()._log_error(error_info)
        
        # Log additional details
        self.logger.debug(f"Error category: {error_info.category.value}")
        self.logger.debug(f"Error severity: {error_info.severity.value}")
        self.logger.debug(f"Recoverable: {error_info.recoverable}")
        
        if error_info.retry_after:
            self.logger.debug(f"Suggested retry after: {error_info.retry_after}s")
        
        if self.include_stack_trace:
            import traceback
            self.logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        
        if error_info.context:
            self.logger.debug(f"Error context: {error_info.context}")
