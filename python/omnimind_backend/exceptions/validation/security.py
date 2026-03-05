"""Security validation exceptions.

Exceptions for security checks, permission validation,
and security policy violations.
"""

from __future__ import annotations

from omnimind_backend.exceptions.base.business import ValidationError


class SecurityValidationError(ValidationError):
    """Security validation failure."""
    
    def __init__(
        self,
        message: str,
        *,
        security_policy: str | None = None,
        violation_type: str | None = None,
        risk_level: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            component="validation",
            **kwargs
        )
        self.security_policy = security_policy
        self.violation_type = violation_type
        self.risk_level = risk_level
