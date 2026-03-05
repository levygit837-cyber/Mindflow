"""Input sanitization exceptions.

Exceptions for input cleaning, XSS prevention,
and data sanitization failures.
"""

from __future__ import annotations

from omnimind_backend.exceptions.base.business import ValidationError


class SanitizationError(ValidationError):
    """Input sanitization failure."""
    
    def __init__(
        self,
        message: str,
        *,
        input_type: str | None = None,
        sanitization_rule: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            component="validation",
            **kwargs
        )
        self.input_type = input_type
        self.sanitization_rule = sanitization_rule
