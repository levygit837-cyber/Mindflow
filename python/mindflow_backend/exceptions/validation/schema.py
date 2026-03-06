"""Schema validation exceptions.

Exceptions for Pydantic schema validation, data structure validation,
and format checking errors.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business import ValidationError


class SchemaError(ValidationError):
    """Schema validation failure."""
    
    def __init__(
        self,
        message: str,
        *,
        schema_name: str | None = None,
        field_name: str | None = None,
        validation_rule: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            field=field_name,
            validation_rule=validation_rule,
            component="validation",
            **kwargs
        )
        self.schema_name = schema_name
