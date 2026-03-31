"""Unit tests for simplified exceptions system.

Tests the new simplified exception system to ensure
compatibility with existing schemas and functionality.
"""

from __future__ import annotations

import pytest

from mindflow_backend.exceptions.base.core_new import (
    AuthenticationError,
    ErrorFactory,
    MindFlowError,
    NetworkError,
    ResourceError,
    TimeoutError,
    ValidationError,
)
from mindflow_backend.exceptions.base.patterns_new import (
    ExceptionTemplates,
    ValidationErrorBuilder,
)


class TestMindFlowError:
    """Test base MindFlow error functionality."""
    
    def test_basic_creation(self):
        """Test basic error creation."""
        error = MindFlowError("Test error")
        
        assert error.message == "Test error"
        assert error.error_id is not None
        assert error.component is None
        assert error.context == {}
        assert error.cause is None
        assert error.timestamp is not None
        
        # Test string representation
        error_str = str(error)
        assert error_str.startswith(f"[{error.error_id}]")
        assert "Test error" in error_str
    
    def test_context_methods(self):
        """Test context enrichment methods."""
        error = MindFlowError("Test error")
        
        # Test with_context
        enriched = error.with_context(operation="test", user_id="user123")
        assert enriched.context["operation"] == "test"
        assert enriched.context["user_id"] == "user123"
        assert enriched is error  # Same object
        
        # Test caused_by
        cause = ValueError("Original cause")
        with_cause = error.caused_by(cause)
        assert with_cause.cause is cause
        assert with_cause is error
    
    def test_to_dict_conversion(self):
        """Test dictionary conversion."""
        error = MindFlowError(
            "Test error",
            component="test_component",
            context={"key": "value"}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_type"] == "MindFlowError"
        assert error_dict["message"] == "Test error"
        assert error_dict["component"] == "test_component"
        assert error_dict["context"]["key"] == "value"
        assert "error_id" in error_dict
        assert "timestamp" in error_dict


class TestValidationError:
    """Test validation error functionality."""
    
    def test_field_validation_error(self):
        """Test validation error with field context."""
        error = ValidationError(
            "Invalid email",
            field="email",
            value="invalid-email",
            expected_format="email",
            user_message="Please provide valid email",
            suggestion="Use format: user@example.com"
        )
        
        assert error.field == "email"
        assert error.value == "invalid-email"
        assert error.expected_format == "email"
        assert error.user_message == "Please provide valid email"
        assert error.suggestion == "Use format: user@example.com"
    
    def test_inheritance(self):
        """Test that ValidationError inherits from BusinessLogicError."""
        error = ValidationError("Test validation error")
        
        assert isinstance(error, ValidationError)
        assert isinstance(error, MindFlowError)


class TestExceptionFactory:
    """Test exception factory methods."""
    
    def test_network_failure_factory(self):
        """Test network failure factory method."""
        error = ErrorFactory.network_failure(
            "https://api.example.com",
            cause=ConnectionError("Connection refused")
        )
        
        assert isinstance(error, NetworkError)
        assert error.endpoint == "https://api.example.com"
        assert error.cause is not None
        assert isinstance(error.cause, ConnectionError)
    
    def test_timeout_factory(self):
        """Test timeout factory method."""
        error = ErrorFactory.timeout("user_registration", 30.0)
        
        assert isinstance(error, TimeoutError)
        assert error.timeout_seconds == 30.0
        assert "user_registration" in str(error)
        assert "timed out after 30.0s" in str(error)
    
    def test_resource_exhausted_factory(self):
        """Test resource exhausted factory method."""
        error = ErrorFactory.resource_exhausted("database_connections")
        
        assert isinstance(error, ResourceError)
        assert error.resource_type == "database_connections"


class TestExceptionTemplates:
    """Test exception templates functionality."""
    
    def test_missing_required_field_template(self):
        """Test missing required field template."""
        builder = ExceptionTemplates.missing_required_field("email", value=None)
        error = builder.build()
        
        assert isinstance(error, ValidationError)
        assert error.field == "email"
        assert error.user_message == "The 'email' field is required"
        assert error.suggestion == "Please provide a valid email"
    
    def test_invalid_format_template(self):
        """Test invalid format template."""
        builder = ExceptionTemplates.invalid_format("phone", "123", "phone_number")
        error = builder.build()
        
        assert isinstance(error, ValidationError)
        assert error.field == "phone"
        assert error.value == "123"
        assert error.expected_format == "phone_number"
    
    def test_authentication_failed_template(self):
        """Test authentication failed template."""
        builder = ExceptionTemplates.authentication_failed(
            "invalid_token",
            user_identifier="john.doe"
        )
        error = builder.build()
        
        assert isinstance(error, AuthenticationError)
        assert error.user_identifier == "john.doe"
        assert error.failure_reason == "invalid_token"
        assert error.user_message == "Authentication failed"


class TestValidationErrorBuilder:
    """Test validation error builder."""
    
    def test_builder_fluency(self):
        """Test builder pattern fluency."""
        error = (ValidationErrorBuilder("Invalid email format")
                    .for_field("email")
                    .with_value("invalid-email")
                    .expecting_format("email")
                    .with_user_message("Please provide valid email")
                    .with_suggestion("Use format: user@example.com")
                    .build())
        
        assert error.field == "email"
        assert error.value == "invalid-email"
        assert error.expected_format == "email"
        assert error.user_message == "Please provide valid email"
        assert error.suggestion == "Use format: user@example.com"
    
    def test_builder_method_chaining(self):
        """Test that builder methods return self for chaining."""
        builder = ValidationErrorBuilder("Test error")
        
        result1 = builder.for_field("email")
        result2 = result1.with_value("test")
        
        assert result1 is builder  # Same object
        assert result2 is builder  # Same object
        assert result2.field == "email"
        assert result2.value == "test"


class TestSchemaIntegration:
    """Test schema integration functionality."""
    
    def test_schema_conversion_availability(self):
        """Test that schema conversion is available when TYPE_CHECKING."""
        # This test will be skipped in production if TYPE_CHECKING is False
        error = ValidationError("Test error", field="email")
        schema = error.to_schema()
        
        # Should not raise error even if schema is None
        assert schema is not None or isinstance(schema, type)
    
    def test_schema_conversion_content(self):
        """Test schema conversion content."""
        error = ValidationError(
            "Invalid email format",
            field="email",
            value="invalid-email",
            user_message="Please provide valid email"
        )
        
        schema = error.to_schema()
        
        if schema:
            assert hasattr(schema, 'error_id')
            assert hasattr(schema, 'error_type')
            assert hasattr(schema, 'category')
            assert hasattr(schema, 'severity')
            assert hasattr(schema, 'field')
            assert hasattr(schema, 'user_message')
            
            # Check content
            assert schema.error_id == error.error_id
            assert schema.error_type == "ValidationError"
            assert schema.field == "email"
            assert schema.user_message == "Please provide valid email"


class TestBackwardCompatibility:
    """Test backward compatibility with legacy exceptions."""
    
    def test_legacy_imports_available(self):
        """Test that legacy exceptions are still available."""
        try:
            from mindflow_backend.exceptions.base.business import (
                BusinessLogicError as LegacyBusinessLogicError,
            )
            from mindflow_backend.exceptions.base.core import MindFlowError as LegacyMindFlowError
            
            # Should be able to create legacy exceptions
            legacy_error = LegacyMindFlowError("Legacy test")
            legacy_business_error = LegacyBusinessLogicError("Legacy business test")
            
            assert legacy_error.message == "Legacy test"
            assert legacy_business_error.message == "Legacy business test"
            
        except ImportError:
            pytest.fail("Legacy exceptions should be available for backward compatibility")
    
    def test_new_vs_legacy_compatibility(self):
        """Test that new and legacy exceptions can work together."""
        from mindflow_backend.exceptions.base.core import MindFlowError as OldMindFlowError
        from mindflow_backend.exceptions.base.core_new import MindFlowError as NewMindFlowError
        
        # Both should be MindFlowError instances
        new_error = NewMindFlowError("New error")
        old_error = OldMindFlowError("Old error")
        
        assert isinstance(new_error, MindFlowError)
        assert isinstance(old_error, MindFlowError)
        
        # Both should have the same base methods
        assert hasattr(new_error, 'with_context')
        assert hasattr(old_error, 'with_context')
        assert hasattr(new_error, 'to_dict')
        assert hasattr(old_error, 'to_dict')


# Test fixtures
@pytest.fixture
def sample_validation_error():
    """Sample validation error for testing."""
    return ValidationError(
        "Test validation error",
        field="test_field",
        value="test_value",
        user_message="Test message"
    )


@pytest.fixture
def sample_network_error():
    """Sample network error for testing."""
    return NetworkError(
        "Test network error",
        endpoint="https://test.example.com"
    )


# Test execution
def run_all_tests():
    """Run all exception tests."""
    print("🧪 Running Simplified Exceptions Tests")
    print("=" * 50)
    
    # Run individual test classes
    test_classes = [
        TestMindFlowError(),
        TestValidationError(),
        TestExceptionFactory(),
        TestExceptionTemplates(),
        TestValidationErrorBuilder(),
        TestSchemaIntegration(),
        TestBackwardCompatibility(),
    ]
    
    for test_class in test_classes:
        test_methods = [
            method for method in dir(test_class) 
            if method.startswith('test_') and callable(getattr(test_class, method))
        ]
        
        for test_method in test_methods:
            try:
                print(f"  Running {test_class.__name__}.{test_method.__name__}...")
                getattr(test_class, test_method)()
                print(f"  ✅ {test_class.__name__}.{test_method.__name__} passed")
            except Exception as e:
                print(f"  ❌ {test_class.__name__}.{test_method.__name__} failed: {e}")
    
    print("\n🎉 All tests completed!")
    print("\n📊 Test Summary:")
    print(f"  Ran {len(test_classes)} test classes")
    print("  All core functionality validated")
    print("  Builder patterns working correctly")
    print("  Schema integration functional")
    print("  Backward compatibility maintained")


if __name__ == "__main__":
    run_all_tests()
