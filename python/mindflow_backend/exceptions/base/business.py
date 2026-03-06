"""Business logic exceptions for MindFlow.

Exceptions related to business rules, validation, and workflow errors.
These are expected errors that should be handled gracefully by the user interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .core import MindFlowError


class BusinessLogicError(MindFlowError):
    """Base exception for business logic errors.
    
    Used for errors that are part of normal business operations
    and should be communicated to users in a friendly way.
    """
    
    def __init__(
        self,
        message: str,
        *,
        user_message: Optional[str] = None,
        error_code: Optional[str] = None,
        severity: str = "low",
        recoverable: bool = True,
        **kwargs: Any,
    ):
        super().__init__(message, severity=severity, recoverable=recoverable, **kwargs)
        self.user_message = user_message or message
        self.error_code = error_code


class ValidationError(BusinessLogicError):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="low", **kwargs)
        self.field = field
        self.value = value
        self.validation_rule = validation_rule


class AuthenticationError(BusinessLogicError):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        auth_method: Optional[str] = None,
        user_identifier: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.auth_method = auth_method
        self.user_identifier = user_identifier


class AuthorizationError(BusinessLogicError):
    """Raised when user lacks permission for an operation."""
    
    def __init__(
        self,
        message: str = "Access denied",
        *,
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.required_permission = required_permission
        self.resource = resource


class BusinessRuleError(BusinessLogicError):
    """Raised when a business rule is violated."""
    
    def __init__(
        self,
        message: str,
        *,
        rule_name: Optional[str] = None,
        rule_description: Optional[str] = None,
        violated_condition: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.rule_name = rule_name
        self.rule_description = rule_description
        self.violated_condition = violated_condition


class WorkflowError(BusinessLogicError):
    """Raised when workflow execution fails."""
    
    def __init__(
        self,
        message: str,
        *,
        workflow_step: Optional[str] = None,
        workflow_state: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.workflow_step = workflow_step
        self.workflow_state = workflow_state
        self.next_steps = next_steps or []


class DomainError(BusinessLogicError):
    """Raised when domain-specific constraints are violated."""
    
    def __init__(
        self,
        message: str,
        *,
        domain: Optional[str] = None,
        constraint: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.domain = domain
        self.constraint = constraint


class ConflictError(BusinessLogicError):
    """Raised when there's a conflict with existing state."""
    
    def __init__(
        self,
        message: str,
        *,
        conflicting_resource: Optional[str] = None,
        conflict_type: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.conflicting_resource = conflicting_resource
        self.conflict_type = conflict_type


class NotFoundError(BusinessLogicError):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        message: str,
        *,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="low", **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id
