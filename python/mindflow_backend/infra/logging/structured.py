"""Advanced structured logging with correlation and sampling.

Enhanced logging system with correlation IDs, log sampling,
and production-ready configuration.
"""

from __future__ import annotations

import logging
import sys
import random
from typing import TYPE_CHECKING, Optional, Dict, Any
from contextvars import ContextVar

import structlog
from structlog.stdlib import LoggerFactory
from structlog.processors import JSONRenderer

# ConsoleRenderer was removed in newer structlog versions
try:
    from structlog.processors import ConsoleRenderer
except ImportError:
    # Fallback for newer structlog versions
    from structlog.dev import ConsoleRenderer

from mindflow_backend.infra.logging.correlation import get_correlation_manager
from mindflow_backend.infra.logging.sampling import get_log_sampler
from mindflow_backend.infra.config import get_settings

if TYPE_CHECKING:
    pass

# Context variable for correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog + stdlib logging with advanced features.
    
    Args:
        level: Logging level to configure
    """
    global _configured
    if _configured:
        return
    _configured = True

    settings = get_settings()
    correlation_manager = get_correlation_manager()
    log_sampler = get_log_sampler()

    # Shared processors for both renderers
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_correlation_id,
        _add_sampling_info,
        _add_environment_info,
    ]

    # Choose renderer based on configuration
    if settings.log_format == "json":
        renderer: structlog.types.Processor = JSONRenderer()
    else:
        renderer = ConsoleRenderer()

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Configure stdlib logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)

    # Configure correlation manager
    correlation_manager.configure()

    # Configure log sampler
    log_sampler.configure(
        sample_rate=getattr(settings, 'log_sampling_rate', 1.0),
        debug_mode=settings.is_development,
    )

    _logger = structlog.get_logger(__name__)
    _logger.info(
        "logging_configured",
        level=level,
        format=settings.log_format,
        correlation_enabled=True,
        sampling_enabled=True,
    )


def _add_correlation_id(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add correlation ID to log event.
    
    Args:
        logger: Logger instance
        method_name: Method name
        event_dict: Event dictionary
        
    Returns:
        Updated event dictionary with correlation ID
    """
    correlation_id = _correlation_id.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def _add_sampling_info(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add sampling information to log event.
    
    Args:
        logger: Logger instance
        method_name: Method name
        event_dict: Event dictionary
        
    Returns:
        Updated event dictionary with sampling info
    """
    log_sampler = get_log_sampler()
    if log_sampler.should_sample(event_dict):
        event_dict["sampled"] = True
    else:
        event_dict["sampled"] = False
    return event_dict


def _add_environment_info(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add environment information to log event.
    
    Args:
        logger: Logger instance
        method_name: Method name
        event_dict: Event dictionary
        
    Returns:
        Updated event dictionary with environment info
    """
    settings = get_settings()
    event_dict.update({
        "environment": settings.app_env,
        "service": settings.app_name,
        "version": getattr(settings, 'app_version', '1.0.0'),
    })
    return event_dict


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog bound logger with correlation and sampling.
    
    Args:
        name: Logger name
        
    Returns:
        Structlog bound logger with enhanced features
    """
    return structlog.get_logger(name)


def get_logger_with_correlation(name: str, correlation_id: str) -> structlog.stdlib.BoundLogger:
    """Get logger with specific correlation ID.
    
    Args:
        name: Logger name
        correlation_id: Correlation ID to use
        
    Returns:
        Logger with correlation ID set
    """
    token = _correlation_id.set(correlation_id)
    try:
        logger = get_logger(name)
        return logger.bind(correlation_id=correlation_id)
    finally:
        _correlation_id.reset(token)


def reset_logging() -> None:
    """Reset the configured flag (for testing)."""
    global _configured
    _configured = False


class LoggingContext:
    """Context manager for logging with correlation ID.
    
    Provides automatic correlation ID management for request/response cycles.
    """
    
    def __init__(self, correlation_id: Optional[str] = None, **context: Any):
        """Initialize logging context.
        
        Args:
            correlation_id: Optional correlation ID
            **context: Additional context to bind to logger
        """
        self.correlation_id = correlation_id
        self.context = context
        self.token: Optional[Any] = None
        self.logger = get_logger(__name__)
        
    def __enter__(self) -> "LoggingContext":
        """Enter context and set correlation ID."""
        correlation_manager = get_correlation_manager()
        
        if not self.correlation_id:
            self.correlation_id = correlation_manager.generate_correlation_id()
            
        self.token = _correlation_id.set(self.correlation_id)
        
        # Bind context to logger
        if self.context:
            self.logger = self.logger.bind(**self.context)
            
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and reset correlation ID."""
        if self.token:
            _correlation_id.reset(self.token)
            
        # Log exception if present
        if exc_type is not None:
            self.logger.error(
                "context_exception",
                exc_type=exc_type.__name__,
                exc_msg=str(exc_val),
                correlation_id=self.correlation_id,
            )


def with_correlation_id(correlation_id: str, **context: Any) -> LoggingContext:
    """Create logging context with correlation ID.
    
    Args:
        correlation_id: Correlation ID to use
        **context: Additional context
        
    Returns:
        LoggingContext instance
    """
    return LoggingContext(correlation_id=correlation_id, **context)


def with_logging_context(**context: Any) -> LoggingContext:
    """Create logging context with auto-generated correlation ID.
    
    Args:
        **context: Additional context
        
    Returns:
        LoggingContext instance with auto-generated correlation ID
    """
    return LoggingContext(**context)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context.
    
    Args:
        correlation_id: Correlation ID to set
    """
    _correlation_id.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID.
    
    Returns:
        Current correlation ID or None
    """
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear current correlation ID."""
    _correlation_id.set(None)


# Enhanced logging functions for common patterns
def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs: Any
) -> None:
    """Log HTTP request with correlation and timing.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    logger = get_logger("http.request")
    logger.info(
        "http_request_completed",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> None:
    """Log error with correlation and context.
    
    Args:
        error: Exception to log
        context: Additional context
        **kwargs: Additional context
    """
    logger = get_logger("error")
    error_context = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "error_module": error.__class__.__module__,
    }
    
    if context:
        error_context.update(context)
        
    error_context.update(kwargs)
    
    logger.error("error_occurred", **error_context)


def log_performance(
    operation: str,
    duration_ms: float,
    success: bool = True,
    **kwargs: Any
) -> None:
    """Log performance metric with correlation.
    
    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds
        success: Whether operation succeeded
        **kwargs: Additional context
    """
    logger = get_logger("performance")
    logger.info(
        "performance_metric",
        operation=operation,
        duration_ms=duration_ms,
        success=success,
        **kwargs
    )


def log_business_event(
    event_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs: Any
) -> None:
    """Log business event with correlation.
    
    Args:
        event_name: Business event name
        user_id: Optional user ID
        session_id: Optional session ID
        **kwargs: Additional context
    """
    logger = get_logger("business")
    context = {
        "event_name": event_name,
    }
    
    if user_id:
        context["user_id"] = user_id
    if session_id:
        context["session_id"] = session_id
        
    context.update(kwargs)
    
    logger.info("business_event", **context)
