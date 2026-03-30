"""Backward-compatibility shim for exceptions.base.business.

Re-exports all classes from business_new.py. New code should import
directly from `mindflow_backend.exceptions.base.business_new` or the
top-level `mindflow_backend.exceptions` package.
"""

from __future__ import annotations

from .business_new import (
    BusinessLogicError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
)


class WorkflowError(BusinessLogicError):
    """Workflow-related business logic errors.

    Used for errors occurring during orchestrated workflow execution,
    e.g. invalid state transitions, dependency failures, etc.
    """

    def __init__(self, message: str, *, workflow_id: str | None = None, step: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.workflow_id = workflow_id
        self.step = step


__all__ = [
    "BusinessLogicError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "WorkflowError",
]
