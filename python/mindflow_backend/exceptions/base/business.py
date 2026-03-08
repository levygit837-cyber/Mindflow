"""Business logic exceptions for MindFlow.

Exceptions related to business rules, validation, and workflow errors.
These are expected errors that should be handled gracefully by the user interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

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
        self.suggestion = None
        self.business_context = {}
    
    def with_user_message(self, user_message: str) -> BusinessLogicError:
        """Set user-friendly message."""
        self.user_message = user_message
        return self
    
    def with_error_code(self, error_code: str) -> BusinessLogicError:
        """Set business error code."""
        self.error_code = error_code
        return self
    
    def with_severity(self, severity: str) -> BusinessLogicError:
        """Set error severity."""
        self.severity = severity
        return self
    
    def set_recoverable(self, recoverable: bool) -> BusinessLogicError:
        """Set whether error is recoverable."""
        self.recoverable = recoverable
        return self
    
    def with_suggestion(self, suggestion: str) -> BusinessLogicError:
        """Add recovery suggestion."""
        self.suggestion = suggestion
        return self
    
    def with_business_context(self, **context: Any) -> BusinessLogicError:
        """Add business-specific context."""
        self.business_context.update(context)
        return self
    
    def to_response_schema(self) -> Dict[str, Any]:
        """Convert to API response schema format."""
        return self.as_user_error()


class ValidationError(BusinessLogicError):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        expected_type: Optional[str] = None,
        expected_format: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="low", **kwargs)
        self.field = field
        self.value = value
        self.validation_rule = validation_rule
        self.expected_type = expected_type
        self.expected_format = expected_format
    
    def for_field(self, field: str) -> ValidationError:
        """Set field that failed validation."""
        self.field = field
        return self
    
    def with_value(self, value: Any) -> ValidationError:
        """Set the value that failed validation."""
        self.value = value
        return self
    
    def with_rule(self, validation_rule: str) -> ValidationError:
        """Set validation rule that failed."""
        self.validation_rule = validation_rule
        return self
    
    def expecting_type(self, expected_type: str) -> ValidationError:
        """Set expected data type."""
        self.expected_type = expected_type
        return self
    
    def expecting_format(self, expected_format: str) -> ValidationError:
        """Set expected format."""
        self.expected_format = expected_format
        return self


class AuthenticationError(BusinessLogicError):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        auth_method: Optional[str] = None,
        user_identifier: Optional[str] = None,
        auth_provider: Optional[str] = None,
        failure_reason: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.auth_method = auth_method
        self.user_identifier = user_identifier
        self.auth_provider = auth_provider
        self.failure_reason = failure_reason
    
    def with_auth_method(self, auth_method: str) -> AuthenticationError:
        """Set authentication method."""
        self.auth_method = auth_method
        return self
    
    def for_user(self, user_identifier: str) -> AuthenticationError:
        """Set user identifier."""
        self.user_identifier = user_identifier
        return self
    
    def from_provider(self, auth_provider: str) -> AuthenticationError:
        """Set authentication provider."""
        self.auth_provider = auth_provider
        return self
    
    def with_failure_reason(self, failure_reason: str) -> AuthenticationError:
        """Set failure reason."""
        self.failure_reason = failure_reason
        return self


class AuthorizationError(BusinessLogicError):
    """Raised when user lacks permission for an operation."""
    
    def __init__(
        self,
        message: str = "Access denied",
        *,
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        user_permissions: Optional[List[str]] = None,
        access_level: Optional[str] = None,
        role: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.required_permission = required_permission
        self.resource = resource
        self.user_permissions = user_permissions
        self.access_level = access_level
        self.role = role
    
    def requiring_permission(self, required_permission: str) -> AuthorizationError:
        """Set required permission."""
        self.required_permission = required_permission
        return self
    
    def for_resource(self, resource: str) -> AuthorizationError:
        """Set resource being accessed."""
        self.resource = resource
        return self
    
    def with_user_permissions(self, permissions: List[str]) -> AuthorizationError:
        """Set user's current permissions."""
        self.user_permissions = permissions
        return self
    
    def requiring_access_level(self, access_level: str) -> AuthorizationError:
        """Set required access level."""
        self.access_level = access_level
        return self
    
    def for_role(self, role: str) -> AuthorizationError:
        """Set user role."""
        self.role = role
        return self


class BusinessRuleError(BusinessLogicError):
    """Raised when a business rule is violated."""
    
    def __init__(
        self,
        message: str,
        *,
        rule_name: Optional[str] = None,
        rule_description: Optional[str] = None,
        violated_condition: Optional[str] = None,
        business_impact: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.rule_name = rule_name
        self.rule_description = rule_description
        self.violated_condition = violated_condition
        self.business_impact = business_impact
    
    def for_rule(self, rule_name: str) -> BusinessRuleError:
        """Set business rule name."""
        self.rule_name = rule_name
        return self
    
    def with_description(self, rule_description: str) -> BusinessRuleError:
        """Set rule description."""
        self.rule_description = rule_description
        return self
    
    def violating_condition(self, violated_condition: str) -> BusinessRuleError:
        """Set violated condition."""
        self.violated_condition = violated_condition
        return self
    
    def with_business_impact(self, business_impact: str) -> BusinessRuleError:
        """Set business impact."""
        self.business_impact = business_impact
        return self


class ConflictError(BusinessLogicError):
    """Raised when there's a conflict with existing state."""
    
    def __init__(
        self,
        message: str,
        *,
        conflicting_resource: Optional[str] = None,
        conflict_type: Optional[str] = None,
        existing_state: Optional[Dict[str, Any]] = None,
        proposed_state: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.conflicting_resource = conflicting_resource
        self.conflict_type = conflict_type
        self.existing_state = existing_state
        self.proposed_state = proposed_state
    
    def for_resource(self, conflicting_resource: str) -> ConflictError:
        """Set conflicting resource."""
        self.conflicting_resource = conflicting_resource
        return self
    
    def of_type(self, conflict_type: str) -> ConflictError:
        """Set conflict type."""
        self.conflict_type = conflict_type
        return self
    
    def with_existing_state(self, existing_state: Dict[str, Any]) -> ConflictError:
        """Set existing conflicting state."""
        self.existing_state = existing_state
        return self
    
    def with_proposed_state(self, proposed_state: Dict[str, Any]) -> ConflictError:
        """Set proposed conflicting state."""
        self.proposed_state = proposed_state
        return self


class DomainError(BusinessLogicError):
    """Raised when domain-specific constraints are violated."""
    
    def __init__(
        self,
        message: str,
        *,
        domain: Optional[str] = None,
        constraint: Optional[str] = None,
        constraint_type: Optional[str] = None,
        domain_context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.domain = domain
        self.constraint = constraint
        self.constraint_type = constraint_type
        self.domain_context = domain_context
    
    def in_domain(self, domain: str) -> DomainError:
        """Set domain where constraint was violated."""
        self.domain = domain
        return self
    
    def violating_constraint(self, constraint: str) -> DomainError:
        """Set violated constraint."""
        self.constraint = constraint
        return self
    
    def of_type(self, constraint_type: str) -> DomainError:
        """Set constraint type."""
        self.constraint_type = constraint_type
        return self
    
    def with_domain_context(self, domain_context: Dict[str, Any]) -> DomainError:
        """Set domain-specific context."""
        self.domain_context = domain_context
        return self


class NotFoundError(BusinessLogicError):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        message: str,
        *,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        search_criteria: Optional[Dict[str, Any]] = None,
        available_resources: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="low", **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.search_criteria = search_criteria
        self.available_resources = available_resources
    
    def for_resource_type(self, resource_type: str) -> NotFoundError:
        """Set resource type."""
        self.resource_type = resource_type
        return self
    
    def with_id(self, resource_id: str) -> NotFoundError:
        """Set resource ID."""
        self.resource_id = resource_id
        return self
    
    def with_search_criteria(self, search_criteria: Dict[str, Any]) -> NotFoundError:
        """Set search criteria used."""
        self.search_criteria = search_criteria
        return self
    
    def with_available_resources(self, available_resources: List[str]) -> NotFoundError:
        """Set list of available resources."""
        self.available_resources = available_resources
        return self


class WorkflowError(BusinessLogicError):
    """Raised when workflow execution fails."""
    
    def __init__(
        self,
        message: str,
        *,
        workflow_step: Optional[str] = None,
        workflow_state: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
        workflow_id: Optional[str] = None,
        step_context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", **kwargs)
        self.workflow_step = workflow_step
        self.workflow_state = workflow_state
        self.next_steps = next_steps
        self.workflow_id = workflow_id
        self.step_context = step_context
    
    def in_step(self, workflow_step: str) -> WorkflowError:
        """Set workflow step that failed."""
        self.workflow_step = workflow_step
        return self
    
    def with_state(self, workflow_state: str) -> WorkflowError:
        """Set current workflow state."""
        self.workflow_state = workflow_state
        return self
    
    def with_next_steps(self, next_steps: List[str]) -> WorkflowError:
        """Set recommended next steps."""
        self.next_steps = next_steps
        return self
    
    def for_workflow(self, workflow_id: str) -> WorkflowError:
        """Set workflow identifier."""
        self.workflow_id = workflow_id
        return self
    
    def with_step_context(self, step_context: Dict[str, Any]) -> WorkflowError:
        """Set step-specific context."""
        self.step_context = step_context
        return self
