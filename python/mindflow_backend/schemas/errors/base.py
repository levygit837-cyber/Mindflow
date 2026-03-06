"""Base error schemas for MindFlow.

Universal error response formats and metadata structures
for consistent error handling and reporting.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorSeverity(str, Enum):
    """Severity levels for system errors."""
    
    LOW = "low"          # Minor issue, doesn't affect core functionality
    MEDIUM = "medium"    # Degrades functionality but system continues
    HIGH = "high"        # Breaks core functionality
    CRITICAL = "critical"  # System unavailable or major failure


class ErrorCategory(str, Enum):
    """Categories of errors for classification and routing."""
    
    # System errors
    SYSTEM = "system"
    INFRASTRUCTURE = "infrastructure"
    NETWORK = "network"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    
    # Business logic errors
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_RULE = "business_rule"
    WORKFLOW = "workflow"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    
    # Agent errors
    AGENT_EXECUTION = "agent_execution"
    AGENT_TIMEOUT = "agent_timeout"
    CONTEXT_RETRIEVAL = "context_retrieval"
    TOOL_EXECUTION = "tool_execution"
    
    # Provider errors
    PROVIDER_ERROR = "provider_error"
    RATE_LIMIT = "rate_limit"
    TOKEN_LIMIT = "token_limit"
    MODEL_UNAVAILABLE = "model_unavailable"
    
    # Orchestrator errors
    ROUTING = "routing"
    DECOMPOSITION = "decomposition"
    SCHEDULING = "scheduling"
    DEPENDENCY = "dependency"


class ErrorContext(BaseModel):
    """Context information for errors."""
    
    component: str = Field(description="Component where error occurred")
    operation: Optional[str] = Field(default=None, description="Operation being performed")
    session_id: Optional[str] = Field(default=None, description="User session ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    request_id: Optional[str] = Field(default=None, description="Request tracking ID")
    trace_id: Optional[str] = Field(default=None, description="Distributed trace ID")
    
    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    
    class Config:
        extra = "allow"


class ErrorSchema(BaseModel):
    """Universal error schema for all MindFlow errors."""
    
    # Identification
    error_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique error identifier")
    error_type: str = Field(description="Exception class name")
    error_code: str = Field(description="Machine-readable error code")
    
    # Classification
    category: ErrorCategory = Field(description="Error category for routing/handling")
    severity: ErrorSeverity = Field(description="Error severity level")
    
    # Messages
    message: str = Field(description="Technical error message")
    user_message: Optional[str] = Field(default=None, description="User-friendly error message")
    
    # Timing and tracking
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When error occurred")
    component: str = Field(description="Component where error originated")
    
    # Context
    context: ErrorContext = Field(description="Error context information")
    
    # Recovery information
    recoverable: bool = Field(description="Whether error is recoverable")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts allowed")
    
    # Technical details
    stack_trace: Optional[str] = Field(default=None, description="Full stack trace")
    cause: Optional[str] = Field(default=None, description="Root cause error")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional error metadata")
    
    class Config:
        extra = "allow"
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        *,
        category: ErrorCategory,
        severity: ErrorSeverity,
        error_code: str,
        component: str,
        context: Optional[ErrorContext] = None,
        user_message: Optional[str] = None,
        recoverable: bool = True,
        **metadata: Any,
    ) -> ErrorSchema:
        """Create error schema from exception."""
        import traceback
        
        # Extract context from exception if it's an MindFlow error
        exception_context = {}
        if hasattr(exception, 'context'):
            exception_context = getattr(exception, 'context', {})
        if hasattr(exception, 'session_id'):
            exception_context['session_id'] = getattr(exception, 'session_id')
        if hasattr(exception, 'user_id'):
            exception_context['user_id'] = getattr(exception, 'user_id')
        
        # Merge with provided context
        if context:
            merged_metadata = {**exception_context, **context.metadata}
            context.metadata = merged_metadata
        else:
            context = ErrorContext(
                component=component,
                metadata=exception_context
            )
        
        return cls(
            error_type=exception.__class__.__name__,
            error_code=error_code,
            category=category,
            severity=severity,
            message=str(exception),
            user_message=user_message or str(exception),
            component=component,
            context=context,
            recoverable=recoverable,
            stack_trace=traceback.format_exc(),
            cause=str(exception.__cause__) if exception.__cause__ else None,
            metadata=metadata,
        )


class ErrorResponse(BaseModel):
    """Standard API error response format."""
    
    success: bool = Field(default=False, description="Always false for error responses")
    error: ErrorSchema = Field(description="Error details")
    
    # Request information
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    # Additional response data
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional response data")
    
    class Config:
        extra = "allow"
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ErrorListResponse(BaseModel):
    """Response format for multiple errors (e.g., validation errors)."""
    
    success: bool = Field(default=False, description="Always false for error responses")
    errors: List[ErrorSchema] = Field(description="List of errors")
    
    # Request information
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    # Summary information
    total_errors: int = Field(description="Total number of errors")
    error_summary: Dict[str, int] = Field(default_factory=dict, description="Error count by category")
    
    class Config:
        extra = "allow"
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def __init__(self, **data: Any):
        super().__init__(**data)
        self.total_errors = len(self.errors)
        self.error_summary = {}
        for error in self.errors:
            category = error.category.value
            self.error_summary[category] = self.error_summary.get(category, 0) + 1
