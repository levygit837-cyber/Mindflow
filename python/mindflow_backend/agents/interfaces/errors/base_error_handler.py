"""Base error handler interface.

Defines the fundamental contract that all error handlers must satisfy,
providing consistent error processing, classification, and response
generation across the MindFlow system.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, Union
from abc import abstractmethod

from mindflow_backend.schemas.errors import (
    ErrorSchema,
    ErrorCategory,
    ErrorSeverity,
    ErrorResponse,
    ErrorListResponse,
)


@runtime_checkable
class BaseErrorHandlerContract(Protocol):
    """Base contract for all error handler implementations.
    
    Every error handler in the system must implement this contract
    to ensure consistent error processing, classification, and response
    generation across different components and contexts.
    """

    @abstractmethod
    async def handle_error(
        self,
        exception: Exception,
        *,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        component: Optional[str] = None,
        operation: Optional[str] = None,
        **metadata: Any,
    ) -> ErrorSchema:
        """Handle an exception and convert it to a structured error schema.
        
        Args:
            exception: The exception to handle
            context: Additional context information
            user_id: User identifier for tracking
            session_id: Session identifier for tracking
            component: Component where error occurred
            operation: Operation being performed
            **metadata: Additional metadata
            
        Returns:
            Structured error schema with full context
        """
        ...

    @abstractmethod
    def classify_error(self, exception: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify an exception into category and severity.
        
        Args:
            exception: The exception to classify
            
        Returns:
            Tuple of (category, severity) for the exception
        """
        ...

    @abstractmethod
    def generate_error_code(self, exception: Exception, category: ErrorCategory) -> str:
        """Generate a machine-readable error code for the exception.
        
        Args:
            exception: The exception to generate code for
            category: The error category
            
        Returns:
            Machine-readable error code
        """
        ...

    @abstractmethod
    def create_error_response(
        self,
        error_schema: ErrorSchema,
        *,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """Create a standardized API error response.
        
        Args:
            error_schema: The error schema to include
            request_id: Request tracking ID
            additional_data: Additional response data
            
        Returns:
            Standardized error response for API
        """
        ...

    @abstractmethod
    def is_recoverable(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if an error is recoverable.
        
        Args:
            exception: The exception to evaluate
            context: Additional context for decision
            
        Returns:
            True if the error is recoverable
        """
        ...

    @abstractmethod
    def get_retry_strategy(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get retry strategy for recoverable errors.
        
        Args:
            exception: The exception to get strategy for
            context: Additional context for strategy decision
            
        Returns:
            Retry strategy configuration or None if not retryable
        """
        ...

    @abstractmethod
    async def log_error(
        self,
        error_schema: ErrorSchema,
        *,
        level: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an error with appropriate level and context.
        
        Args:
            error_schema: The error schema to log
            level: Log level (INFO, WARNING, ERROR, CRITICAL)
            additional_context: Additional logging context
        """
        ...

    @abstractmethod
    def enhance_context(
        self,
        exception: Exception,
        base_context: Dict[str, Any],
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        component: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enhance error context with additional information.
        
        Args:
            exception: The exception being handled
            base_context: Base context to enhance
            user_id: User identifier
            session_id: Session identifier
            component: Component name
            operation: Operation name
            
        Returns:
            Enhanced context dictionary
        """
        ...

    @abstractmethod
    def should_propagate(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if an error should be propagated up the call stack.
        
        Args:
            exception: The exception to evaluate
            context: Additional context for decision
            
        Returns:
            True if the error should be propagated
        """
        ...

    @abstractmethod
    def create_user_message(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a user-friendly error message.
        
        Args:
            exception: The exception to create message for
            context: Additional context for message generation
            
        Returns:
            User-friendly error message or None
        """
        ...

    @abstractmethod
    def get_suggested_actions(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[list[str]]:
        """Get suggested actions for error resolution.
        
        Args:
            exception: The exception to get suggestions for
            context: Additional context for suggestions
            
        Returns:
            List of suggested actions or None
        """
        ...

    # Optional convenience methods
    
    def handle_multiple_errors(
        self,
        exceptions: list[Exception],
        *,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        component: Optional[str] = None,
        operation: Optional[str] = None,
        **metadata: Any,
    ) -> ErrorListResponse:
        """Handle multiple exceptions and create a batch error response.
        
        Default implementation calls handle_error for each exception.
        Subclasses can override for optimized batch handling.
        
        Args:
            exceptions: List of exceptions to handle
            context: Additional context information
            user_id: User identifier for tracking
            session_id: Session identifier for tracking
            component: Component where errors occurred
            operation: Operation being performed
            **metadata: Additional metadata
            
        Returns:
            Error list response with all errors
        """
        error_schemas = []
        
        for exception in exceptions:
            error_schema = self.handle_error(
                exception=exception,
                context=context,
                user_id=user_id,
                session_id=session_id,
                component=component,
                operation=operation,
                **metadata
            )
            error_schemas.append(error_schema)
        
        return ErrorListResponse(
            errors=error_schemas,
            request_id=metadata.get("request_id"),
        )

    def create_error_summary(
        self,
        error_schema: ErrorSchema,
        *,
        include_stack_trace: bool = False,
        include_context: bool = True,
        max_context_items: int = 10,
    ) -> Dict[str, Any]:
        """Create a concise error summary for logging and monitoring.
        
        Args:
            error_schema: The error schema to summarize
            include_stack_trace: Whether to include stack trace
            include_context: Whether to include context
            max_context_items: Maximum context items to include
            
        Returns:
            Error summary dictionary
        """
        summary = {
            "error_id": error_schema.error_id,
            "error_type": error_schema.error_type,
            "error_code": error_schema.error_code,
            "category": error_schema.category.value,
            "severity": error_schema.severity.value,
            "message": error_schema.message,
            "component": error_schema.component,
            "recoverable": error_schema.recoverable,
            "timestamp": error_schema.timestamp.isoformat(),
        }
        
        if include_context and error_schema.context:
            context_items = dict(list(error_schema.context.metadata.items())[:max_context_items])
            summary["context"] = context_items
        
        if include_stack_trace and error_schema.stack_trace:
            summary["stack_trace"] = error_schema.stack_trace
        
        return summary
