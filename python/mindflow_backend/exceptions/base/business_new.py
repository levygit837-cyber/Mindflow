# Business logic exceptions for MindFlow
# Simplified business exceptions following examples pattern

"""Business logic exceptions for MindFlow.

Simplified business exceptions following examples pattern.
"""

from __future__ import annotations

from typing import Any

from .core_new import MindFlowError


class BusinessLogicError(MindFlowError):
    """Base exception for business logic errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, component="business", **kwargs)


class ValidationError(BusinessLogicError):
    """Validation errors for user input and data."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: Any = None,
        expected_format: str | None = None,
        validation_rule: str | None = None,
        user_message: str | None = None,
        suggestion: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.expected_format = expected_format
        self.validation_rule = validation_rule
        self.user_message = user_message
        self.suggestion = suggestion


class AuthenticationError(BusinessLogicError):
    """Authentication and authorization errors."""

    def __init__(
        self,
        message: str,
        *,
        user_identifier: str | None = None,
        auth_method: str | None = None,
        auth_provider: str | None = None,
        failure_reason: str | None = None,
        error_code: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.user_identifier = user_identifier
        self.auth_method = auth_method
        self.auth_provider = auth_provider
        self.failure_reason = failure_reason
        self.error_code = error_code


class AuthorizationError(AuthenticationError):
    """Authorization and permission errors."""

    def __init__(
        self,
        message: str,
        *,
        required_permission: str | None = None,
        resource: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.required_permission = required_permission
        self.resource = resource


class NotFoundError(BusinessLogicError):
    """Resource not found errors."""

    def __init__(
        self,
        message: str,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id


class WorkflowError(BusinessLogicError):
    """Workflow-related business logic errors.

    Used for errors occurring during orchestrated workflow execution,
    e.g. invalid state transitions, dependency failures, etc.
    """

    def __init__(self, message: str, *, workflow_id: str | None = None, step: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.workflow_id = workflow_id
        self.step = step
