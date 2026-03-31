"""Logging interfaces for MindFlow components.

Provides standardized interfaces for consistent logging across all components,
with support for structured logging, log levels, and monitoring integration.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class LogLevel(Enum):
    """Log levels for MindFlow components."""
    
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    TRACE = "trace"


@dataclass
class LogEntry:
    """Structured log entry."""
    
    timestamp: datetime
    level: LogLevel
    message: str
    component: str
    context: dict[str, Any] | None = None
    error: Exception | None = None
    correlation_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert log entry to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "component": self.component,
            "context": self.context,
            "error": str(self.error) if self.error else None,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
        }


@dataclass
class LogMetrics:
    """Logging metrics for monitoring."""
    
    total_logs: int = 0
    error_count: int = 0
    warning_count: int = 0
    last_log_time: datetime | None = None
    logs_by_level: dict[LogLevel, int] = None
    
    def __post_init__(self):
        if self.logs_by_level is None:
            self.logs_by_level = {level: 0 for level in LogLevel}


@runtime_checkable
class LoggableInterface(Protocol):
    """Interface for components with standardized logging capabilities.
    
    Provides consistent logging methods that include component context,
    structured data, and integration with monitoring systems.
    """
    
    def log_operation(self, operation: str, **kwargs) -> None:
        """Log a service operation with context.
        
        Args:
            operation: Name of the operation being performed
            **kwargs: Additional context data for logging
        """
        ...
    
    def log_error(self, error: Exception, context: str = "", **kwargs) -> None:
        """Log an error with full context.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            **kwargs: Additional context data
        """
        ...
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log a warning message.
        
        Args:
            message: Warning message
            **kwargs: Additional context data
        """
        ...
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log an informational message.
        
        Args:
            message: Info message
            **kwargs: Additional context data
        """
        ...
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log a debug message.
        
        Args:
            message: Debug message
            **kwargs: Additional context data
        """
        ...
    
    def set_log_level(self, level: LogLevel) -> None:
        """Set the logging level for this component.
        
        Args:
            level: New log level
        """
        ...
    
    def get_log_level(self) -> LogLevel:
        """Get the current logging level.
        
        Returns:
            Current log level
        """
        ...
    
    def get_log_metrics(self) -> LogMetrics:
        """Get logging metrics for monitoring.
        
        Returns:
            Metrics about logging activity
        """
        ...


@runtime_checkable
class StructuredLoggingInterface(LoggableInterface, Protocol):
    """Interface for components with advanced structured logging.
    
    Extends basic logging with structured data support, correlation tracking,
    and integration with observability platforms.
    """
    
    def log_structured(self, level: LogLevel, message: str, **context) -> None:
        """Log a structured message with context.
        
        Args:
            level: Log level
            message: Log message
            **context: Structured context data
        """
        ...
    
    def with_context(self, **context) -> StructuredLoggingInterface:
        """Create a logger with additional context.
        
        Args:
            **context: Context to add to all log messages
            
        Returns:
            Logger with additional context
        """
        ...
    
    def with_correlation_id(self, correlation_id: str) -> StructuredLoggingInterface:
        """Create a logger with correlation ID.
        
        Args:
            correlation_id: Correlation ID for request tracking
            
        Returns:
            Logger with correlation ID
        """
        ...
    
    def log_performance(self, operation: str, duration: float, **context) -> None:
        """Log performance metrics.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
            **context: Additional context
        """
        ...
    
    def log_user_action(self, user_id: str, action: str, **context) -> None:
        """Log a user action.
        
        Args:
            user_id: User identifier
            action: Action performed
            **context: Additional context
        """
        ...
    
    def log_security_event(self, event_type: str, severity: str, **context) -> None:
        """Log a security event.
        
        Args:
            event_type: Type of security event
            severity: Event severity
            **context: Security context
        """
        ...


@runtime_checkable
class LogSinkInterface(Protocol):
    """Interface for log sinks that handle log output.
    
    Defines how log entries are processed, filtered, and sent to
    various destinations like files, databases, or external services.
    """
    
    async def write_log(self, entry: LogEntry) -> None:
        """Write a log entry to the sink.
        
        Args:
            entry: Log entry to write
        """
        ...
    
    async def write_logs(self, entries: list[LogEntry]) -> None:
        """Write multiple log entries to the sink.
        
        Args:
            entries: Log entries to write
        """
        ...
    
    def should_log(self, entry: LogEntry) -> bool:
        """Check if a log entry should be written by this sink.
        
        Args:
            entry: Log entry to check
            
        Returns:
            True if entry should be written
        """
        ...
    
    async def flush(self) -> None:
        """Flush any pending log entries."""
        ...
    
    async def close(self) -> None:
        """Close the log sink and cleanup resources."""
        ...


@runtime_checkable
class LoggingContextInterface(Protocol):
    """Interface for managing logging context across operations.
    
    Provides context management for correlation IDs, user sessions,
    and request tracking across component boundaries.
    """
    
    def get_correlation_id(self) -> str | None:
        """Get the current correlation ID.
        
        Returns:
            Current correlation ID or None
        """
        ...
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set the correlation ID for the current context.
        
        Args:
            correlation_id: Correlation ID to set
        """
        ...
    
    def get_user_id(self) -> str | None:
        """Get the current user ID.
        
        Returns:
            Current user ID or None
        """
        ...
    
    def set_user_id(self, user_id: str) -> None:
        """Set the user ID for the current context.
        
        Args:
            user_id: User ID to set
        """
        ...
    
    def get_session_id(self) -> str | None:
        """Get the current session ID.
        
        Returns:
            Current session ID or None
        """
        ...
    
    def set_session_id(self, session_id: str) -> None:
        """Set the session ID for the current context.
        
        Args:
            session_id: Session ID to set
        """
        ...
    
    def with_context(self, **context) -> AbstractContextManager[LoggingContextInterface]:
        """Create a context manager with additional context.
        
        Args:
            **context: Context to add
            
        Returns:
            Context manager
        """
        ...
    
    async def with_async_context(self, **context) -> AbstractAsyncContextManager[LoggingContextInterface]:
        """Create an async context manager with additional context.
        
        Args:
            **context: Context to add
            
        Returns:
            Async context manager
        """
        ...


@runtime_checkable
class LogAnalyticsInterface(Protocol):
    """Interface for log analytics and monitoring.
    
    Provides capabilities for analyzing log patterns, detecting anomalies,
    and generating insights from log data.
    """
    
    async def query_logs(self, query: str, time_range: tuple[datetime, datetime]) -> list[LogEntry]:
        """Query logs based on search criteria.
        
        Args:
            query: Search query
            time_range: Time range to search
            
        Returns:
            Matching log entries
        """
        ...
    
    async def get_error_patterns(self, time_range: tuple[datetime, datetime]) -> dict[str, int]:
        """Get error patterns from logs.
        
        Args:
            time_range: Time range to analyze
            
        Returns:
            Dictionary of error patterns and their counts
        """
        ...
    
    async def get_performance_metrics(self, operation: str, time_range: tuple[datetime, datetime]) -> dict[str, float]:
        """Get performance metrics from logs.
        
        Args:
            operation: Operation to analyze
            time_range: Time range to analyze
            
        Returns:
            Performance metrics (avg, min, max, p95, p99)
        """
        ...
    
    async def detect_anomalies(self, time_range: tuple[datetime, datetime]) -> list[dict[str, Any]]:
        """Detect anomalies in log patterns.
        
        Args:
            time_range: Time range to analyze
            
        Returns:
            List of detected anomalies
        """
        ...
    
    async def generate_log_report(self, time_range: tuple[datetime, datetime]) -> dict[str, Any]:
        """Generate comprehensive log report.
        
        Args:
            time_range: Time range for report
            
        Returns:
            Comprehensive log analytics report
        """
        ...
