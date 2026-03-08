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

from .base_error_handler import BaseErrorHandlerContract


@runtime_checkable
class ValidationErrorHandlerContract(BaseErrorHandlerContract, Protocol):
    """Contract for validation-related error handling.
    
    Specialized interface for handling input validation, schema validation,
    data sanitization, and security validation errors.
    """

    @abstractmethod
    async def handle_validation_error(
        self,
        exception: Exception,
        *,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        expected_type: Optional[str] = None,
        expected_format: Optional[str] = None,
        **context: Any,
    ) -> ValidationErrorSchema:
        """Handle field validation errors.
        
        Args:
            exception: The validation exception
            field: Field that failed validation
            value: Value that failed validation
            validation_rule: Validation rule that was violated
            expected_type: Expected data type
            expected_format: Expected format (email, phone, etc.)
            **context: Additional context
            
        Returns:
            Validation error schema with field context
        """
        ...

    @abstractmethod
    async def handle_schema_error(
        self,
        exception: Exception,
        *,
        schema_name: Optional[str] = None,
        schema_path: Optional[str] = None,
        validation_path: Optional[str] = None,
        invalid_fields: Optional[List[str]] = None,
        missing_fields: Optional[List[str]] = None,
        **context: Any,
    ) -> SchemaErrorSchema:
        """Handle schema validation errors.
        
        Args:
            exception: The schema validation exception
            schema_name: Name of the schema that failed
            schema_path: Path to schema definition
            validation_path: Path in schema where validation failed
            invalid_fields: List of invalid field names
            missing_fields: List of missing required fields
            **context: Additional context
            
        Returns:
            Schema error schema with validation context
        """
        ...

    @abstractmethod
    async def handle_sanitization_error(
        self,
        exception: Exception,
        *,
        input_data: Optional[str] = None,
        sanitization_rule: Optional[str] = None,
        detected_issue: Optional[str] = None,
        severity_level: Optional[str] = None,
        **context: Any,
    ) -> SanitizationErrorSchema:
        """Handle data sanitization errors.
        
        Args:
            exception: The sanitization exception
            input_data: Input data that failed sanitization
            sanitization_rule: Sanitization rule that failed
            detected_issue: Type of issue detected
            severity_level: Security severity level
            **context: Additional context
            
        Returns:
            Sanitization error schema with security context
        """
        ...

    @abstractmethod
    async def handle_security_validation_error(
        self,
        exception: Exception,
        *,
        security_rule: Optional[str] = None,
        threat_type: Optional[str] = None,
        blocked_content: Optional[str] = None,
        risk_level: Optional[str] = None,
        **context: Any,
    ) -> SecurityValidationErrorSchema:
        """Handle security validation errors.
        
        Args:
            exception: The security validation exception
            security_rule: Security rule that was violated
            threat_type: Type of security threat detected
            blocked_content: Content that was blocked
            risk_level: Security risk level
            **context: Additional context
            
        Returns:
            Security validation error schema with threat context
        """
        ...

    @abstractmethod
    async def handle_request_validation_error(
        self,
        exception: Exception,
        *,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        content_type: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        field_errors: Optional[Dict[str, str]] = None,
        **context: Any,
    ) -> RequestValidationErrorSchema:
        """Handle API request validation errors.
        
        Args:
            exception: The request validation exception
            endpoint: API endpoint being validated
            http_method: HTTP method
            content_type: Request content type
            validation_errors: Detailed validation errors
            field_errors: Field-specific error messages
            **context: Additional context
            
        Returns:
            Request validation error schema with API context
        """
        ...

    @abstractmethod
    def get_validation_rules(
        self,
        schema_name: str,
        field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get validation rules for a schema or field.
        
        Args:
            schema_name: Schema name to get rules for
            field: Specific field to get rules for
            
        Returns:
            Validation rules dictionary
        """
        ...

    @abstractmethod
    def validate_input_format(
        self,
        input_data: Any,
        expected_format: str,
        *,
        strict: bool = False,
    ) -> Dict[str, Any]:
        """Validate input data format.
        
        Args:
            input_data: Input data to validate
            expected_format: Expected format (email, phone, date, etc.)
            strict: Whether to use strict validation
            
        Returns:
            Validation result with details
        """
        ...

    @abstractmethod
    def sanitize_input(
        self,
        input_data: Any,
        sanitization_level: str = "standard",
    ) -> Dict[str, Any]:
        """Sanitize input data according to security rules.
        
        Args:
            input_data: Input data to sanitize
            sanitization_level: Level of sanitization (lenient, standard, strict)
            
        Returns:
            Sanitization result with cleaned data
        """
        ...

    @abstractmethod
    def get_field_suggestions(
        self,
        field: str,
        value: Any,
        validation_error: str,
    ) -> List[str]:
        """Get suggestions for fixing validation errors.
        
        Args:
            field: Field name that failed validation
            value: Value that failed validation
            validation_error: Validation error message
            
        Returns:
            List of suggestions for fixing the error
        """
        ...

    @abstractmethod
    def get_schema_documentation(
        self,
        schema_name: str,
        field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get documentation for a schema or field.
        
        Args:
            schema_name: Schema name to get documentation for
            field: Specific field to get documentation for
            
        Returns:
            Schema documentation
        """
        ...

    @abstractmethod
    def validate_business_rules(
        self,
        data: Dict[str, Any],
        rules: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate business rules against data.
        
        Args:
            data: Data to validate against business rules
            rules: List of business rule names to validate
            context: Additional context for validation
            
        Returns:
            Business rule validation result
        """
        ...

    # Validation-specific convenience methods
    
    def batch_validate(
        self,
        data_items: List[Dict[str, Any]],
        schema_name: str,
        *,
        stop_on_first_error: bool = False,
    ) -> Dict[str, Any]:
        """Validate multiple data items against a schema.
        
        Args:
            data_items: List of data items to validate
            schema_name: Schema name for validation
            stop_on_first_error: Stop on first validation error
            
        Returns:
            Batch validation results
        """
        # Default implementation - subclasses should override
        results = {
            "valid_count": 0,
            "invalid_count": 0,
            "errors": [],
            "valid_items": [],
            "invalid_items": [],
        }
        
        for i, item in enumerate(data_items):
            try:
                # Placeholder for actual validation logic
                results["valid_count"] += 1
                results["valid_items"].append({"index": i, "item": item})
            except Exception as e:
                results["invalid_count"] += 1
                results["invalid_items"].append({"index": i, "item": item, "error": str(e)})
                results["errors"].append({"index": i, "error": str(e)})
                
                if stop_on_first_error:
                    break
        
        return results

    def get_validation_statistics(
        self,
        schema_name: str,
        time_range: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get validation statistics for monitoring.
        
        Args:
            schema_name: Schema name to get statistics for
            time_range: Time range for statistics (1h, 24h, 7d, etc.)
            
        Returns:
            Validation statistics
        """
        # Default implementation - subclasses should override
        return {
            "schema_name": schema_name,
            "time_range": time_range,
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "success_rate": 0.0,
            "common_errors": [],
            "average_validation_time": 0.0,
        }

    def create_validation_report(
        self,
        validation_results: List[Dict[str, Any]],
        schema_name: str,
    ) -> Dict[str, Any]:
        """Create a comprehensive validation report.
        
        Args:
            validation_results: List of validation results
            schema_name: Schema name being validated
            
        Returns:
            Validation report with statistics and recommendations
        """
        # Default implementation - subclasses should override
        total = len(validation_results)
        passed = sum(1 for result in validation_results if result.get("valid", False))
        failed = total - passed
        
        return {
            "schema_name": schema_name,
            "total_validations": total,
            "passed_validations": passed,
            "failed_validations": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "common_errors": [],
            "recommendations": [],
            "validation_time": None,
        }
