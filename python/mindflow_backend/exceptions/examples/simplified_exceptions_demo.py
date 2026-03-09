"""Simplified Exceptions Demo.

Demonstrates the new simplified exception system with
practical patterns and essential functionality.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from mindflow_backend.exceptions.base.core_new import (
    MindFlowError,
    SystemError,
    NetworkError,
    TimeoutError,
    ResourceError,
    ErrorFactory,
)
from mindflow_backend.exceptions.base.business_new import (
    BusinessLogicError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
)
from mindflow_backend.exceptions.base.patterns_new import (
    ExceptionTemplates,
)


def demo_basic_usage():
    """Demonstrate basic exception usage."""
    print("🎯 Basic Usage Demo")
    print("=" * 50)
    
    # Simple error creation
    error = MindFlowError(
        "Database connection failed",
        component="database",
        context={"host": "localhost", "port": 5432}
    )
    
    print(f"✅ Created basic error:")
    print(f"   Error ID: {error.error_id}")
    print(f"   Component: {error.component}")
    print(f"   Context: {error.context}")
    print(f"   Timestamp: {error.timestamp}")
    
    # Validation error with field context
    validation_error = ValidationError(
        "Invalid email format",
        field="email",
        value="invalid-email",
        expected_format="email",
        user_message="Please provide a valid email address",
        suggestion="Use format: user@example.com"
    )
    
    print(f"\n✅ Validation error:")
    print(f"   Field: {validation_error.field}")
    print(f"   Value: {validation_error.value}")
    print(f"   Expected: {validation_error.expected_format}")
    print(f"   User message: {validation_error.user_message}")


def demo_factory_methods():
    """Demonstrate factory method usage."""
    print("\n🏭 Factory Methods Demo")
    print("=" * 50)
    
    # Network failure
    network_error = ErrorFactory.network_failure(
        "https://api.example.com/users",
        cause=ConnectionError("Connection refused")
    )
    
    print(f"✅ Network failure from factory:")
    print(f"   Message: {network_error}")
    print(f"   Endpoint: {network_error.endpoint}")
    print(f"   Cause: {network_error.cause}")
    
    # Timeout error
    timeout_error = ErrorFactory.timeout(
        "user_registration",
        30.0
    )
    
    print(f"\n✅ Timeout error from factory:")
    print(f"   Message: {timeout_error}")
    print(f"   Operation: user_registration")
    print(f"   Timeout: {timeout_error.timeout_seconds}s")
    
    # Resource exhaustion
    resource_error = ErrorFactory.resource_exhausted("database_connections")
    
    print(f"\n✅ Resource error from factory:")
    print(f"   Message: {resource_error}")
    print(f"   Resource type: {resource_error.resource_type}")


def demo_exception_templates():
    """Demonstrate exception templates."""
    print("\n📋 Exception Templates Demo")
    print("=" * 50)
    
    # Missing required field
    missing_field_error = ExceptionTemplates.missing_required_field(
        "email",
        value=None
    ).build()
    
    print(f"✅ Missing field template:")
    print(f"   Field: {missing_field_error.field}")
    print(f"   User message: {missing_field_error.user_message}")
    print(f"   Suggestion: {missing_field_error.suggestion}")
    
    # Invalid format
    invalid_format_error = ExceptionTemplates.invalid_format(
        "phone",
        "123",
        "phone_number"
    ).build()
    
    print(f"\n✅ Invalid format template:")
    print(f"   Field: {invalid_format_error.field}")
    print(f"   Value: {invalid_format_error.value}")
    print(f"   Expected: {invalid_format_error.expected_format}")
    
    # Authentication failed
    auth_failed_error = ExceptionTemplates.authentication_failed(
        "invalid_token",
        user_identifier="john.doe"
    ).build()
    
    print(f"\n✅ Authentication failed template:")
    print(f"   Error code: {auth_failed_error.error_code}")
    print(f"   User message: {auth_failed_error.user_message}")
    print(f"   Suggestion: {auth_failed_error.suggestion}")


def demo_context_methods():
    """Demonstrate context methods."""
    print("\n🔧 Context Methods Demo")
    print("=" * 50)
    
    # Base error with context
    base_error = MindFlowError("Processing failed")
    
    # Add context using fluent interface
    context_enriched_error = (base_error
        .with_context(
            operation="data_processing",
            step="validation",
            user_id="user123",
            session_id="session456"
        )
        .caused_by(ValueError("Invalid input data"))
    )
    
    print(f"✅ Context-enriched error:")
    print(f"   Original: {context_enriched_error}")
    print(f"   Context: {context_enriched_error.context}")
    print(f"   Cause: {context_enriched_error.cause}")


async def demo_error_handling():
    """Demonstrate error handling in async context."""
    print("\n⚡ Async Error Handling Demo")
    print("=" * 50)
    
    async def risky_operation():
        await asyncio.sleep(0.1)  # Simulate work
        
        # Simulate different error types
        import random
        error_type = random.choice(["validation", "network", "timeout", "resource"])
        
        if error_type == "validation":
            raise ValidationError("Invalid user data", field="email")
        elif error_type == "network":
            raise NetworkError("API request failed", endpoint="https://api.example.com")
        elif error_type == "timeout":
            raise TimeoutError("Operation timed out", timeout_seconds=30.0)
        else:
            raise ResourceError("Database exhausted", resource_type="database")
        
        return "Operation successful"
    
    # Demonstrate error handling
    try:
        result = await risky_operation()
        print(f"✅ Operation result: {result}")
        
    except Exception as exc:
        print(f"\n✅ Caught exception:")
        print(f"   Type: {type(exc).__name__}")
        print(f"   Message: {str(exc)}")
        
        # Check if it's our enhanced exception
        if hasattr(exc, 'error_id'):
            print(f"   Error ID: {exc.error_id}")
            if hasattr(exc, 'context'):
                print(f"   Context: {exc.context}")
            if hasattr(exc, 'component'):
                print(f"   Component: {exc.component}")


def demo_user_friendly_responses():
    """Demonstrate user-friendly error responses."""
    print("\n👤 User-Friendly Responses Demo")
    print("=" * 50)
    
    # Create various errors
    errors = [
        ValidationError("Invalid email format")
            .with_field("email")
            .with_value("invalid-email")
            .expecting_format("email")
            .with_user_message("Please provide a valid email address")
            .with_suggestion("Use format: user@example.com"),
        
        NotFoundError("User not found")
            .with_resource_type("User")
            .with_id("12345")
            .with_user_message("We couldn't find the user you're looking for")
            .with_suggestion("Check the user ID and try again"),
        
        AuthorizationError("Access denied")
            .with_required_permission("admin_access")
            .for_resource("admin_panel")
            .with_user_message("You don't have permission to access admin panel")
            .with_suggestion("Contact your administrator if you need access"),
    ]
    
    for i, error in enumerate(errors, 1):
        print(f"\n✅ User Response {i}:")
        print(f"   Message: {error.user_message}")
        print(f"   Field: {getattr(error, 'field', 'N/A')}")
        print(f"   Suggestion: {getattr(error, 'suggestion', 'None')}")
        print(f"   Error ID: {getattr(error, 'error_id', 'N/A')}")


async def main():
    """Run all demos."""
    print("🚀 Simplified Exceptions System Demo")
    print("=" * 60)
    print("Demonstrating simplified, practical exception handling")
    print("without over-engineering while maintaining essential functionality.")
    print("=" * 60)
    
    demo_basic_usage()
    demo_factory_methods()
    demo_exception_templates()
    demo_context_methods()
    await demo_error_handling()
    demo_user_friendly_responses()
    
    print("\n🎉 Demo Complete!")
    print("Simplified exception features demonstrated successfully.")
    print("\n📚 Key Improvements:")
    print("- Removed complexity while preserving functionality")
    print("- Added factory methods for common patterns")
    print("- Exception templates for recurring errors")
    print("- Context methods for error enrichment")
    print("- User-friendly response formatting")
    print("- Compatible with existing schema system")


if __name__ == "__main__":
    asyncio.run(main())
