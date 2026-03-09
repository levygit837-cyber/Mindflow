"""Validation error handler interface.

Defines contracts for handling input validation errors, schema validation
failures, and data integrity validation problems.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, List, Union
from abc import abstractmethod

from mindflow_backend.schemas.errors import (
    ValidationErrorSchema,
    SchemaErrorSchema,
    SanitizationErrorSchema,
    SecurityValidationErrorSchema,
    RequestValidationErrorSchema,
    ErrorCategory,
    ErrorSeverity,
)

from .base import BaseErrorHandlerContract


@runtime_checkable
class ValidationErrorHandlerContract(BaseErrorHandlerContract, Protocol):
    """Contract for validation-related error handling.
    
    Specialized interface for handling input validation, schema validation,
    data sanitization, and security validation errors.
    """
    
    @abstractmethod
    async def validate_input(
        self,
        input_data: Any,
        schema: Dict[str, Any],
        context: Dict[str, Any] | None = None,
    ) -> tuple[bool, List[ValidationErrorSchema]]:
        """Validate input data against schema.
        
        Args:
            input_data: Data to validate
            schema: Validation schema
            context: Optional validation context
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        ...
    
    @abstractmethod
    async def sanitize_data(
        self,
        data: Any,
        sanitization_rules: Dict[str, Any],
    ) -> tuple[Any, List[SanitizationErrorSchema]]:
        """Sanitize data according to rules.
        
        Args:
            data: Data to sanitize
            sanitization_rules: Rules for sanitization
            
        Returns:
            Tuple of (sanitized_data, sanitization_errors)
        """
        ...
    
    @abstractmethod
    async def validate_security_constraints(
        self,
        data: Any,
        security_rules: Dict[str, Any],
    ) -> tuple[bool, List[SecurityValidationErrorSchema]]:
        """Validate security constraints on data.
        
        Args:
            data: Data to validate
            security_rules: Security validation rules
            
        Returns:
            Tuple of (is_valid, security_errors)
        """
        ...
    
    @abstractmethod
    async def handle_validation_failure(
        self,
        error: ValidationErrorSchema,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle validation failure with appropriate response.
        
        Args:
            error: Validation error details
            context: Error context
            
        Returns:
            Error handling response
        """
        ...
