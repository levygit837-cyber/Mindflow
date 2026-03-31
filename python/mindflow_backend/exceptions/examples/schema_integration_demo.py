"""Schema Integration Demo.

Demonstrates simplified exception system integration
with existing Pydantic schemas.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core_new import (
    AuthenticationError,
    MindFlowError,
    NetworkError,
    ResourceError,
    ValidationError,
)
from mindflow_backend.exceptions.base.patterns_new import (
    ExceptionTemplates,
)


def demo_schema_conversion():
    """Demonstrate exception to schema conversion."""
    print("🔄 Schema Conversion Demo")
    print("=" * 50)
    
    # Create validation error
    validation_error = ValidationError(
        "Invalid email format",
        field="email",
        value="invalid-email",
        expected_format="email",
        user_message="Please provide a valid email address",
        suggestion="Use format: user@example.com"
    )
    
    # Convert to schema
    schema = validation_error.to_schema()
    
    if schema:
        print("✅ Converted exception to schema:")
        print(f"   Schema type: {type(schema).__name__}")
        print(f"   Error ID: {schema.error_id}")
        print(f"   Error type: {schema.error_type}")
        print(f"   Category: {schema.category.value}")
        print(f"   Severity: {schema.severity.value}")
        print(f"   Field: {schema.field}")
        print(f"   User message: {schema.user_message}")
    else:
        print("❌ Schema conversion not available (TYPE_CHECKING=False)")


def demo_user_friendly_api_response():
    """Demonstrate user-friendly API error responses."""
    print("\n👤 User-Friendly API Response Demo")
    print("=" * 50)
    
    # Create various errors and convert to API responses
    errors = [
        ValidationError("Invalid email format")
            .with_field("email")
            .with_value("invalid-email")
            .expecting_format("email")
            .with_user_message("Please provide a valid email address")
            .with_suggestion("Use format: user@example.com"),
        
        AuthenticationError("Invalid credentials")
            .with_auth_method("password")
            .for_user("john.doe")
            .from_provider("local")
            .with_failure_reason("invalid_password")
            .with_user_message("Authentication failed")
            .with_suggestion("Please check your credentials"),
        
        NetworkError("API timeout")
            .for_endpoint("https://api.example.com/users")
            .with_timeout(30.0)
            .with_user_message("Request timed out")
            .with_suggestion("Please try again"),
        
        ResourceError("Database exhausted")
            .with_resource_type("connection_pool")
            .with_user_message("Service temporarily unavailable")
            .with_suggestion("Please try again later"),
    ]
    
    for i, error in enumerate(errors, 1):
        # Get user-friendly response
        user_response = error.to_dict() if hasattr(error, 'to_dict') else {
            "message": str(error),
            "error_type": error.__class__.__name__,
        }
        
        print(f"\n✅ API Response {i}:")
        print(f"   Message: {user_response.get('message', 'No message')}")
        print(f"   Error Type: {user_response.get('error_type', 'Unknown')}")
        print(f"   Error ID: {getattr(error, 'error_id', 'N/A')}")


def demo_exception_templates_with_schema():
    """Demonstrate exception templates with schema integration."""
    print("\n📋 Exception Templates with Schema Demo")
    print("=" * 50)
    
    # Missing field template
    missing_field_error = ExceptionTemplates.missing_required_field(
        "email",
        value=None
    ).build()
    
    print("✅ Missing field template:")
    print(f"   Field: {missing_field_error.field}")
    print(f"   User message: {missing_field_error.user_message}")
    print(f"   Suggestion: {missing_field_error.suggestion}")
    
    # Convert to schema
    schema = missing_field_error.to_schema()
    if schema:
        print(f"   Schema: {schema.error_type} - {schema.severity.value}")
    
    # Invalid format template
    invalid_format_error = ExceptionTemplates.invalid_format(
        "phone",
        "123",
        "phone_number"
    ).build()
    
    print("\n✅ Invalid format template:")
    print(f"   Field: {invalid_format_error.field}")
    print(f"   Expected: {invalid_format_error.expected_format}")
    
    # Authentication failed template
    auth_failed_error = ExceptionTemplates.authentication_failed(
        "invalid_token",
        user_identifier="john.doe"
    ).build()
    
    print("\n✅ Authentication failed template:")
    print(f"   Error code: {auth_failed_error.error_code}")
    print(f"   User message: {auth_failed_error.user_message}")
    print(f"   Suggestion: {auth_failed_error.suggestion}")


def demo_error_context_enrichment():
    """Demonstrate error context enrichment."""
    print("\n🔧 Error Context Enrichment Demo")
    print("=" * 50)
    
    # Base error with context
    base_error = MindFlowError("Processing failed")
    
    # Add context using fluent interface
    context_enriched_error = (base_error
        .with_context(
            operation="user_registration",
            step="validation",
            user_id="user123",
            session_id="session456",
            component="auth_service"
        )
        .caused_by(ValueError("Invalid input data"))
    )
    
    print("✅ Context-enriched error:")
    print(f"   Original: {context_enriched_error}")
    print(f"   Context: {context_enriched_error.context}")
    print(f"   Component: {context_enriched_error.component}")
    print(f"   Cause: {context_enriched_error.cause}")
    
    # Check schema conversion
    schema = context_enriched_error.to_schema()
    if schema:
        print(f"   Schema category: {schema.category.value}")
        print(f"   Schema severity: {schema.severity.value}")


def main():
    """Run all demos."""
    print("🚀 Schema Integration Demo")
    print("=" * 60)
    print("Demonstrating simplified exception system")
    print("with existing Pydantic schema integration.")
    print("=" * 60)
    
    demo_schema_conversion()
    demo_user_friendly_api_response()
    demo_exception_templates_with_schema()
    demo_error_context_enrichment()
    
    print("\n🎉 Demo Complete!")
    print("Simplified exception system with schema integration demonstrated.")
    print("\n📚 Key Features:")
    print("- Simplified exception hierarchy")
    print("- Essential context tracking")
    print("- Factory methods for common errors")
    print("- Exception templates for recurring patterns")
    print("- Schema conversion for API responses")
    print("- User-friendly error formatting")
    print("- Full compatibility with existing schemas")


if __name__ == "__main__":
    main()
