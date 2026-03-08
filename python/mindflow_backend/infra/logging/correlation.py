"""Correlation ID management for distributed tracing.

Provides correlation ID generation, propagation, and management
for request tracing across system components.
"""

from __future__ import annotations

import uuid
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from contextvars import ContextVar

import structlog

# IMPORTANT: avoid importing mindflow_backend.infra.logging here to prevent
# circular imports during logging bootstrap.
_logger = structlog.get_logger(__name__)

# Context variables for correlation management
_correlation_chain: ContextVar[list[str]] = ContextVar("correlation_chain", default=[])
_request_start_time: ContextVar[float] = ContextVar("request_start_time", default=0.0)


@dataclass
class CorrelationContext:
    """Correlation context with metadata."""
    correlation_id: str
    parent_id: Optional[str] = None
    chain: list[str] = None
    start_time: float = 0.0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    tags: Dict[str, str] = None
    
    def __post_init__(self) -> None:
        if self.chain is None:
            self.chain = []
        if self.tags is None:
            self.tags = {}
        if self.start_time == 0.0:
            self.start_time = time.time()


class CorrelationManager:
    """Manages correlation IDs for distributed tracing.
    
    Features:
    - Correlation ID generation
    - Chain tracking for nested operations
    - Context propagation
    - Performance tracking
    - User and session association
    """
    
    def __init__(self) -> None:
        """Initialize correlation manager."""
        self._current_context: Optional[CorrelationContext] = None
        self._configured = False
        
    def configure(self) -> None:
        """Configure correlation manager."""
        self._configured = True
        _logger.info("correlation_manager_configured")
        
    def generate_correlation_id(self) -> str:
        """Generate a new correlation ID.
        
        Returns:
            New correlation ID
        """
        return str(uuid.uuid4())
        
    def start_correlation(
        self,
        correlation_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **tags: str
    ) -> CorrelationContext:
        """Start a new correlation context.
        
        Args:
            correlation_id: Optional correlation ID (generated if not provided)
            parent_id: Optional parent correlation ID
            user_id: Optional user ID
            session_id: Optional session ID
            request_id: Optional request ID
            **tags: Additional tags
            
        Returns:
            New correlation context
        """
        if not correlation_id:
            correlation_id = self.generate_correlation_id()
            
        # Get current chain
        current_chain = list(_correlation_chain.get([]))
        
        # Add parent to chain if exists
        if parent_id and parent_id not in current_chain:
            current_chain.append(parent_id)
            
        # Add current correlation to chain
        if correlation_id not in current_chain:
            current_chain.append(correlation_id)
            
        context = CorrelationContext(
            correlation_id=correlation_id,
            parent_id=parent_id,
            chain=current_chain,
            start_time=time.time(),
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            tags=tags,
        )
        
        self._current_context = context
        
        # Set context variables
        _correlation_chain.set(current_chain)
        _request_start_time.set(context.start_time)
        
        _logger.info(
            "correlation_started",
            correlation_id=correlation_id,
            parent_id=parent_id,
            chain_length=len(current_chain),
            user_id=user_id,
            session_id=session_id,
        )
        
        return context
        
    def get_current_context(self) -> Optional[CorrelationContext]:
        """Get current correlation context.
        
        Returns:
            Current correlation context or None
        """
        return self._current_context
        
    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID.
        
        Returns:
            Current correlation ID or None
        """
        context = self.get_current_context()
        return context.correlation_id if context else None
        
    def get_correlation_chain(self) -> list[str]:
        """Get current correlation chain.
        
        Returns:
            Current correlation chain
        """
        return list(_correlation_chain.get([]))
        
    def get_parent_id(self) -> Optional[str]:
        """Get parent correlation ID.
        
        Returns:
            Parent correlation ID or None
        """
        context = self.get_current_context()
        return context.parent_id if context else None
        
    def add_tag(self, key: str, value: str) -> None:
        """Add tag to current correlation context.
        
        Args:
            key: Tag key
            value: Tag value
        """
        context = self.get_current_context()
        if context:
            context.tags[key] = value
            _logger.debug(
                "correlation_tag_added",
                correlation_id=context.correlation_id,
                key=key,
                value=value,
            )
            
    def get_tags(self) -> Dict[str, str]:
        """Get all tags from current context.
        
        Returns:
            Dictionary of tags
        """
        context = self.get_current_context()
        return context.tags if context else {}
        
    def get_tag(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get specific tag from current context.
        
        Args:
            key: Tag key
            default: Default value if tag not found
            
        Returns:
            Tag value or default
        """
        context = self.get_current_context()
        return context.tags.get(key, default) if context else default
        
    def end_correlation(self) -> Optional[CorrelationContext]:
        """End current correlation context.
        
        Returns:
            Ended correlation context or None
        """
        context = self.get_current_context()
        if not context:
            return None
            
        # Calculate duration
        duration = time.time() - context.start_time
        
        _logger.info(
            "correlation_ended",
            correlation_id=context.correlation_id,
            duration_ms=duration * 1000,
            chain_length=len(context.chain),
            tags_count=len(context.tags),
        )
        
        # Clear context
        self._current_context = None
        _correlation_chain.set([])
        _request_start_time.set(0.0)
        
        return context
        
    def create_child_context(
        self,
        operation_name: str,
        **tags: str
    ) -> CorrelationContext:
        """Create child correlation context.
        
        Args:
            operation_name: Name of the operation
            **tags: Additional tags
            
        Returns:
            Child correlation context
        """
        parent_context = self.get_current_context()
        parent_id = parent_context.correlation_id if parent_context else None
        
        # Inherit user and session from parent
        user_id = parent_context.user_id if parent_context else None
        session_id = parent_context.session_id if parent_context else None
        
        # Create child context
        child_context = self.start_correlation(
            parent_id=parent_id,
            user_id=user_id,
            session_id=session_id,
            operation=operation_name,
            **tags
        )
        
        return child_context
        
    def get_request_duration(self) -> float:
        """Get duration of current request.
        
        Returns:
            Request duration in seconds
        """
        start_time = _request_start_time.get()
        if start_time == 0.0:
            return 0.0
        return time.time() - start_time
        
    def get_request_duration_ms(self) -> float:
        """Get duration of current request in milliseconds.
        
        Returns:
            Request duration in milliseconds
        """
        return self.get_request_duration() * 1000
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert current correlation context to dictionary.
        
        Returns:
            Dictionary representation of correlation context
        """
        context = self.get_current_context()
        if not context:
            return {}
            
        return {
            "correlation_id": context.correlation_id,
            "parent_id": context.parent_id,
            "chain": context.chain,
            "start_time": context.start_time,
            "duration_ms": self.get_request_duration_ms(),
            "user_id": context.user_id,
            "session_id": context.session_id,
            "request_id": context.request_id,
            "tags": context.tags,
        }


class CorrelationContextManager:
    """Context manager for correlation management."""
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **tags: str
    ):
        """Initialize correlation context manager.
        
        Args:
            correlation_id: Optional correlation ID
            parent_id: Optional parent correlation ID
            user_id: Optional user ID
            session_id: Optional session ID
            request_id: Optional request ID
            **tags: Additional tags
        """
        self.correlation_id = correlation_id
        self.parent_id = parent_id
        self.user_id = user_id
        self.session_id = session_id
        self.request_id = request_id
        self.tags = tags
        self.manager = get_correlation_manager()
        self.context: Optional[CorrelationContext] = None
        
    def __enter__(self) -> CorrelationContext:
        """Enter correlation context."""
        self.context = self.manager.start_correlation(
            correlation_id=self.correlation_id,
            parent_id=self.parent_id,
            user_id=self.user_id,
            session_id=self.session_id,
            request_id=self.request_id,
            **self.tags
        )
        return self.context
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit correlation context."""
        if self.context:
            if exc_type is not None:
                self.manager.add_tag("error", "true")
                self.manager.add_tag("error_type", exc_type.__name__)
            self.manager.end_correlation()


def with_correlation(
    correlation_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **tags: str
) -> CorrelationContextManager:
    """Create correlation context manager.
    
    Args:
        correlation_id: Optional correlation ID
        parent_id: Optional parent correlation ID
        user_id: Optional user ID
        session_id: Optional session ID
        request_id: Optional request ID
        **tags: Additional tags
        
    Returns:
        CorrelationContextManager instance
    """
    return CorrelationContextManager(
        correlation_id=correlation_id,
        parent_id=parent_id,
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        **tags
    )


def with_child_correlation(operation_name: str, **tags: str) -> CorrelationContextManager:
    """Create child correlation context manager.
    
    Args:
        operation_name: Name of the operation
        **tags: Additional tags
        
    Returns:
        CorrelationContextManager instance for child context
    """
    manager = get_correlation_manager()
    parent_context = manager.get_current_context()
    parent_id = parent_context.correlation_id if parent_context else None
    
    return CorrelationContextManager(
        parent_id=parent_id,
        operation=operation_name,
        **tags
    )


# Global correlation manager instance
_correlation_manager: Optional[CorrelationManager] = None


def get_correlation_manager() -> CorrelationManager:
    """Get global correlation manager instance.
    
    Returns:
        CorrelationManager instance
    """
    global _correlation_manager
    if _correlation_manager is None:
        _correlation_manager = CorrelationManager()
    return _correlation_manager
