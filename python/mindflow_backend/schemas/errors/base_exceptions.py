"""Base exception schemas for MindFlow.

Specialized schemas for core exception classes that were missing from
the original implementation. These provide structured error responses
for the fundamental exception types.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from pydantic import Field

from .base import ErrorSchema, ErrorCategory, ErrorSeverity, ErrorContext


class MindFlowErrorSchema(ErrorSchema):
    """Schema for MindFlowError - base exception for all system errors.
    
    Provides structured error information including:
    - Unique error ID for tracking
    - Error context metadata
    - Timestamp for debugging
    - Component identification
    """
    
    # MindFlowError specific fields
    error_id: str = Field(description="Unique error identifier from exception")
    timestamp: datetime = Field(description="When the error occurred")
    component: Optional[str] = Field(default=None, description="Component where error originated")
    session_id: Optional[str] = Field(default=None, description="User session ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    context: Dict[str, Any] = Field(default_factory=dict, description="Error context metadata")
    cause: Optional[str] = Field(default=None, description="Root cause exception")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class SystemErrorSchema(ErrorSchema):
    """Schema for SystemError - system-level errors.
    
    Used for infrastructure, configuration, and operational errors
    that are not related to business logic.
    """
    
    # SystemError specific fields
    severity: ErrorSeverity = Field(description="Error severity level")
    recoverable: bool = Field(description="Whether the error is recoverable")
    
    # Additional system context
    service: Optional[str] = Field(default=None, description="Service where error occurred")
    operation: Optional[str] = Field(default=None, description="Operation being performed")
    system_state: Optional[Dict[str, Any]] = Field(default=None, description="System state at error time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ConfigurationErrorSchema(SystemErrorSchema):
    """Schema for ConfigurationError - invalid or missing configuration.
    
    Raised when system configuration is invalid or missing.
    """
    
    # ConfigurationError specific fields
    config_key: Optional[str] = Field(default=None, description="Configuration key that caused error")
    expected_type: Optional[str] = Field(default=None, description="Expected configuration type")
    actual_value: Optional[Any] = Field(default=None, description="Actual configuration value")
    config_file: Optional[str] = Field(default=None, description="Configuration file path")
    
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Configuration errors are medium severity")
    recoverable: bool = Field(default=True, description="Configuration errors are typically recoverable")


class InfrastructureErrorSchema(SystemErrorSchema):
    """Schema for InfrastructureError - infrastructure component failures.
    
    Raised when infrastructure components fail (DB, Redis, etc.).
    """
    
    # InfrastructureError specific fields
    service: Optional[str] = Field(default=None, description="Infrastructure service name")
    operation: Optional[str] = Field(default=None, description="Operation being performed")
    endpoint: Optional[str] = Field(default=None, description="Service endpoint")
    health_check: Optional[bool] = Field(default=None, description="Service health status")
    
    severity: ErrorSeverity = Field(default=ErrorSeverity.HIGH, description="Infrastructure errors are high severity")
    recoverable: bool = Field(default=True, description="Infrastructure errors may be recoverable")


class NetworkErrorSchema(SystemErrorSchema):
    """Schema for NetworkError - network operation failures.
    
    Raised when network operations fail.
    """
    
    # NetworkError specific fields
    endpoint: Optional[str] = Field(default=None, description="Network endpoint that failed")
    timeout: Optional[float] = Field(default=None, description="Network timeout in seconds")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    network_state: Optional[Dict[str, Any]] = Field(default=None, description="Network state information")
    
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Network errors are medium severity")
    recoverable: bool = Field(default=True, description="Network errors are typically recoverable")


class ResourceErrorSchema(SystemErrorSchema):
    """Schema for ResourceError - resource exhaustion or unavailability.
    
    Raised when system resources are exhausted or unavailable.
    """
    
    # ResourceError specific fields
    resource_type: Optional[str] = Field(default=None, description="Type of resource that is exhausted")
    current_usage: Optional[str] = Field(default=None, description="Current resource usage")
    resource_limit: Optional[str] = Field(default=None, description="Resource limit")
    allocation_failure: bool = Field(default=False, description="Whether resource allocation failed")
    
    severity: ErrorSeverity = Field(default=ErrorSeverity.HIGH, description="Resource errors are high severity")
    recoverable: bool = Field(default=False, description="Resource errors are typically not recoverable")


class TimeoutErrorSchema(SystemErrorSchema):
    """Schema for TimeoutError - operation timeout failures.
    
    Raised when operations exceed their time limits.
    """
    
    # TimeoutError specific fields
    operation: Optional[str] = Field(default=None, description="Operation that timed out")
    timeout_seconds: Optional[float] = Field(default=None, description="Timeout limit in seconds")
    elapsed_time: Optional[float] = Field(default=None, description="Actual elapsed time")
    timeout_type: Optional[str] = Field(default=None, description="Type of timeout (e.g., connect, read, write)")
    
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Timeout errors are medium severity")
    recoverable: bool = Field(default=True, description="Timeout errors are typically recoverable")


class BusinessLogicErrorSchema(ErrorSchema):
    """Schema for BusinessLogicError - business logic error base.
    
    Used for errors that are part of normal business operations
    and should be communicated to users in a friendly way.
    """
    
    # BusinessLogicError specific fields
    user_message: Optional[str] = Field(default=None, description="User-friendly error message")
    error_code: Optional[str] = Field(default=None, description="Business error code")
    business_context: Optional[Dict[str, Any]] = Field(default=None, description="Business context information")
    
    severity: ErrorSeverity = Field(default=ErrorSeverity.LOW, description="Business logic errors are low severity")
    recoverable: bool = Field(default=True, description="Business logic errors are typically recoverable")


class ValidationErrorSchema(BusinessLogicErrorSchema):
    """Schema for ValidationError - input validation failures.
    
    Raised when input validation fails.
    """
    
    # ValidationError specific fields
    field: Optional[str] = Field(default=None, description="Field that failed validation")
    value: Optional[Any] = Field(default=None, description="Value that failed validation")
    validation_rule: Optional[str] = Field(default=None, description="Validation rule that failed")
    expected_format: Optional[str] = Field(default=None, description="Expected format")
    
    category: ErrorCategory = Field(default=ErrorCategory.VALIDATION, description="Validation errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.LOW, description="Validation errors are low severity")
    recoverable: bool = Field(default=True, description="Validation errors are recoverable")


class AuthenticationErrorSchema(BusinessLogicErrorSchema):
    """Schema for AuthenticationError - authentication failures.
    
    Raised when authentication fails.
    """
    
    # AuthenticationError specific fields
    auth_method: Optional[str] = Field(default=None, description="Authentication method used")
    user_identifier: Optional[str] = Field(default=None, description="User identifier (username, email, etc.)")
    auth_provider: Optional[str] = Field(default=None, description="Authentication provider")
    failure_reason: Optional[str] = Field(default=None, description="Specific authentication failure reason")
    
    category: ErrorCategory = Field(default=ErrorCategory.AUTHENTICATION, description="Authentication errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Authentication errors are medium severity")
    recoverable: bool = Field(default=True, description="Authentication errors are recoverable")


class AuthorizationErrorSchema(BusinessLogicErrorSchema):
    """Schema for AuthorizationError - authorization failures.
    
    Raised when user lacks permission for an operation.
    """
    
    # AuthorizationError specific fields
    required_permission: Optional[str] = Field(default=None, description="Required permission")
    resource: Optional[str] = Field(default=None, description="Resource being accessed")
    user_permissions: Optional[list[str]] = Field(default=None, description="User's current permissions")
    access_level: Optional[str] = Field(default=None, description="Required access level")
    
    category: ErrorCategory = Field(default=ErrorCategory.AUTHORIZATION, description="Authorization errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Authorization errors are medium severity")
    recoverable: bool = Field(default=True, description="Authorization errors are recoverable")


class BusinessRuleErrorSchema(BusinessLogicErrorSchema):
    """Schema for BusinessRuleError - business rule violations.
    
    Raised when a business rule is violated.
    """
    
    # BusinessRuleError specific fields
    rule_name: Optional[str] = Field(default=None, description="Name of the violated business rule")
    rule_description: Optional[str] = Field(default=None, description="Description of the business rule")
    violated_condition: Optional[str] = Field(default=None, description="Specific condition that was violated")
    business_impact: Optional[str] = Field(default=None, description="Business impact of the violation")
    
    category: ErrorCategory = Field(default=ErrorCategory.BUSINESS_RULE, description="Business rule errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Business rule errors are medium severity")
    recoverable: bool = Field(default=True, description="Business rule errors are typically recoverable")


class ConflictErrorSchema(BusinessLogicErrorSchema):
    """Schema for ConflictError - state conflicts.
    
    Raised when there's a conflict with existing state.
    """
    
    # ConflictError specific fields
    conflicting_resource: Optional[str] = Field(default=None, description="Resource in conflict")
    conflict_type: Optional[str] = Field(default=None, description="Type of conflict")
    existing_state: Optional[Dict[str, Any]] = Field(default=None, description="Existing conflicting state")
    proposed_state: Optional[Dict[str, Any]] = Field(default=None, description="Proposed conflicting state")
    
    category: ErrorCategory = Field(default=ErrorCategory.CONFLICT, description="Conflict errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Conflict errors are medium severity")
    recoverable: bool = Field(default=True, description="Conflict errors are typically recoverable")


class DomainErrorSchema(BusinessLogicErrorSchema):
    """Schema for DomainError - domain constraint violations.
    
    Raised when domain-specific constraints are violated.
    """
    
    # DomainError specific fields
    domain: Optional[str] = Field(default=None, description="Domain where constraint was violated")
    constraint: Optional[str] = Field(default=None, description="Violated domain constraint")
    constraint_type: Optional[str] = Field(default=None, description="Type of constraint violation")
    domain_context: Optional[Dict[str, Any]] = Field(default=None, description="Domain-specific context")
    
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Domain errors are medium severity")
    recoverable: bool = Field(default=True, description="Domain errors are typically recoverable")


class NotFoundErrorSchema(BusinessLogicErrorSchema):
    """Schema for NotFoundError - resource not found.
    
    Raised when a requested resource is not found.
    """
    
    # NotFoundError specific fields
    resource_type: Optional[str] = Field(default=None, description="Type of resource that was not found")
    resource_id: Optional[str] = Field(default=None, description="ID of the resource that was not found")
    search_criteria: Optional[Dict[str, Any]] = Field(default=None, description="Search criteria used")
    available_resources: Optional[list[str]] = Field(default=None, description="List of available resources")
    
    category: ErrorCategory = Field(default=ErrorCategory.NOT_FOUND, description="Not found errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.LOW, description="Not found errors are low severity")
    recoverable: bool = Field(default=True, description="Not found errors are recoverable")


class WorkflowErrorSchema(BusinessLogicErrorSchema):
    """Schema for WorkflowError - workflow execution failures.
    
    Raised when workflow execution fails.
    """
    
    # WorkflowError specific fields
    workflow_step: Optional[str] = Field(default=None, description="Workflow step that failed")
    workflow_state: Optional[str] = Field(default=None, description="Current workflow state")
    next_steps: Optional[list[str]] = Field(default=None, description="Recommended next steps")
    workflow_id: Optional[str] = Field(default=None, description="Workflow identifier")
    step_context: Optional[Dict[str, Any]] = Field(default=None, description="Step-specific context")
    
    category: ErrorCategory = Field(default=ErrorCategory.WORKFLOW, description="Workflow errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Workflow errors are medium severity")
    recoverable: bool = Field(default=True, description="Workflow errors are typically recoverable")
