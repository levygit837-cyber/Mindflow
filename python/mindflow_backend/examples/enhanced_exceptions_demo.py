"""Enhanced Exceptions Demo.

Demonstrates the enhanced exception system with fluent interfaces,
builder patterns, and auto-conversion capabilities.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from mindflow_backend.exceptions.base.core import (
    MindFlowError,
    SystemError,
    NetworkError,
    TimeoutError,
    ConfigurationError,
)
from mindflow_backend.exceptions.base.business import (
    BusinessLogicError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
)
from mindflow_backend.exceptions.base.patterns import (
    ExceptionTemplates,
    ErrorContext,
)
from mindflow_backend.schemas.errors import (
    ValidationErrorSchema,
    AuthenticationErrorSchema,
    ErrorCategory,
    ErrorSeverity,
)


def demo_fluent_interfaces():
    """Demonstrate fluent interface methods."""
    print("🎯 Fluent Interface Demo")
    print("=" * 50)
    
    # Basic fluent interface
    error = (MindFlowError("Database connection failed")
             .with_context(database="postgres", host="localhost")
             .track_workflow("user_registration", "db_connect")
             .with_user_context("user123", "session456")
             .with_tags("database", "critical"))
    
    print(f"✅ Created error with fluent interface:")
    print(f"   Error ID: {error.error_id}")
    print(f"   Component: {error.component}")
    print(f"   Context: {error.context}")
    print(f"   Workflow: {error.get_workflow_info()}")
    print(f"   Tags: {error._tags}")
    
    # Validation error with fluent interface
    validation_error = (ValidationError("Invalid email format")
                       .for_field("email")
                       .with_value("invalid-email")
                       .expecting_format("email")
                       .with_user_message("Please provide a valid email address")
                       .with_suggestion("Use format: user@example.com"))
    
    print(f"\n✅ Validation error with fluent interface:")
    print(f"   Field: {validation_error.field}")
    print(f"   Value: {validation_error.value}")
    print(f"   Expected format: {validation_error.expected_format}")
    print(f"   User message: {validation_error.user_message}")
    print(f"   Suggestion: {validation_error.suggestion}")


def demo_builder_patterns():
    """Demonstrate builder pattern usage."""
    print("\n🏗️ Builder Pattern Demo")
    print("=" * 50)
    
    # Using builder for complex exception
    auth_error = (AuthenticationError.builder("Authentication failed")
                 .with_auth_method("oauth2")
                 .for_user("john.doe")
                 .from_provider("google")
                 .with_failure_reason("invalid_token")
                 .with_user_context("user123", "session456")
                 .with_error_code("AUTH_001")
                 .with_suggestion("Please refresh your access token")
                 .with_tags("authentication", "oauth", "google")
                 .build())
    
    print(f"✅ Built authentication error:")
    print(f"   Message: {auth_error.message}")
    print(f"   Auth method: {auth_error.auth_method}")
    print(f"   User: {auth_error.user_identifier}")
    print(f"   Provider: {auth_error.auth_provider}")
    print(f"   Error code: {auth_error.error_code}")
    print(f"   Suggestion: {auth_error.suggestion}")
    
    # Network error with builder
    network_error = (NetworkError.builder("API request failed")
                     .for_endpoint("https://api.example.com/users")
                     .with_timeout(30.0)
                     .with_retry_count(3)
                     .for_component("api_client")
                     .track_workflow("user_sync", "api_call")
                     .set_recoverable(True)
                     .build())
    
    print(f"\n✅ Built network error:")
    print(f"   Endpoint: {network_error.endpoint}")
    print(f"   Timeout: {network_error.timeout}")
    print(f"   Retry count: {network_error.retry_count}")
    print(f"   Recoverable: {network_error.recoverable}")


def demo_templates():
    """Demonstrate exception templates."""
    print("\n📋 Exception Templates Demo")
    print("=" * 50)
    
    # Using templates for common errors
    missing_field_error = ExceptionTemplates.missing_required_field(
        "email", 
        value=None
    ).build()
    
    print(f"✅ Missing field template:")
    print(f"   Field: {missing_field_error.field}")
    print(f"   User message: {missing_field_error.user_message}")
    print(f"   Suggestion: {missing_field_error.suggestion}")
    
    # Invalid format template
    invalid_format_error = ExceptionTemplates.invalid_format(
        "phone",
        "123",
        "phone_number"
    ).build()
    
    print(f"\n✅ Invalid format template:")
    print(f"   Field: {invalid_format_error.field}")
    print(f"   Value: {invalid_format_error.value}")
    print(f"   Expected format: {invalid_format_error.expected_format}")
    print(f"   User message: {invalid_format_error.user_message}")
    
    # Authentication failed template
    auth_failed_error = ExceptionTemplates.authentication_failed(
        "password",
        user_identifier="john.doe"
    ).build()
    
    print(f"\n✅ Authentication failed template:")
    print(f"   Error code: {auth_failed_error.error_code}")
    print(f"   User message: {auth_failed_error.user_message}")
    print(f"   Suggestion: {auth_failed_error.suggestion}")
    print(f"   Context: {auth_failed_error.context}")


def demo_schema_conversion():
    """Demonstrate auto-conversion to schemas."""
    print("\n🔄 Schema Conversion Demo")
    print("=" * 50)
    
    # Create validation error
    validation_error = ValidationError("Invalid email address")
    validation_error.field = "email"
    validation_error.value = "invalid-email"
    validation_error.validation_rule = "email_format"
    validation_error.user_message = "Please provide a valid email address"
    validation_error.suggestion = "Use format: user@example.com"
    
    # Convert to schema
    schema = validation_error.to_schema()
    
    print(f"✅ Converted exception to schema:")
    print(f"   Schema type: {type(schema).__name__}")
    print(f"   Error ID: {schema.error_id}")
    print(f"   Error type: {schema.error_type}")
    print(f"   Category: {schema.category.value}")
    print(f"   Severity: {schema.severity.value}")
    print(f"   Field: {schema.field}")
    print(f"   Value: {schema.value}")
    print(f"   User message: {schema.user_message}")
    
    # Authentication error with schema association
    auth_error = (AuthenticationError.builder("Invalid credentials")
                 .with_auth_method("password")
                 .for_user("john.doe")
                 .with_schema(AuthenticationErrorSchema)
                 .build())
    
    auth_schema = auth_error.to_schema()
    
    print(f"\n✅ Authentication error with associated schema:")
    print(f"   Schema type: {type(auth_schema).__name__}")
    print(f"   Auth method: {auth_schema.auth_method}")
    print(f"   User identifier: {auth_schema.user_identifier}")
    print(f"   Failure reason: {getattr(auth_schema, 'failure_reason', None)}")


def demo_user_friendly_responses():
    """Demonstrate user-friendly error responses."""
    print("\n👤 User-Friendly Responses Demo")
    print("=" * 50)
    
    # Create various errors
    errors = [
        ValidationError("Invalid email format")
        .for_field("email")
        .with_value("invalid-email")
        .expecting_format("email")
        .with_user_message("Please provide a valid email address")
        .with_suggestion("Use format: user@example.com"),
        
        NotFoundError("User not found")
        .for_resource_type("User")
        .with_id("12345")
        .with_user_message("We couldn't find the user you're looking for")
        .with_suggestion("Check the user ID and try again"),
        
        AuthorizationError("Access denied")
        .requiring_permission("admin_access")
        .for_resource("admin_panel")
        .with_user_message("You don't have permission to access the admin panel")
        .with_suggestion("Contact your administrator if you need access"),
    ]
    
    for i, error in enumerate(errors, 1):
        user_response = error.as_user_error()
        print(f"\n✅ User Response {i}:")
        print(f"   Message: {user_response['message']}")
        print(f"   Error code: {user_response['error_code']}")
        print(f"   Suggestion: {user_response['suggestion']}")
        print(f"   Recoverable: {user_response['recoverable']}")
        print(f"   Error ID: {user_response['error_id']}")


async def demo_error_context():
    """Demonstrate enhanced error context manager."""
    print("\n🔧 Error Context Manager Demo")
    print("=" * 50)
    
    async def risky_operation(should_fail: bool = True):
        """Simulate a risky operation that might fail."""
        await asyncio.sleep(0.1)  # Simulate work
        
        if should_fail:
            raise (NetworkError("Connection timeout")
                    .for_endpoint("https://api.example.com")
                    .with_timeout(30.0)
                    .track_workflow("data_sync", "api_call"))
        
        return "Operation successful"
    
    # Use error context manager
    try:
        async with ErrorContext(
            operation="data_sync",
            component="api_client",
            session_id="session123",
            user_id="user456",
            track_performance=True,
            enable_retry=True,
            max_retries=2,
        ) as context:
            result = await risky_operation(should_fail=True)
            print(f"✅ Operation result: {result}")
            
    except Exception as exc:
        print(f"✅ Caught enhanced exception:")
        print(f"   Error type: {type(exc).__name__}")
        print(f"   Error ID: {getattr(exc, 'error_id', None)}")
        print(f"   Context: {getattr(exc, 'context', {})}")
        print(f"   Workflow info: {getattr(exc, 'get_workflow_info', lambda: {})()}")
        print(f"   Retry count: {context.get('retry_count', 0)}")


def demo_category_and_severity():
    """Demonstrate automatic category and severity detection."""
    print("\n🏷️ Category & Severity Detection Demo")
    print("=" * 50)
    
    errors = [
        ValidationError("Invalid input"),
        NetworkError("Connection failed"),
        TimeoutError("Operation timed out"),
        AuthenticationError("Auth failed"),
        NotFoundError("Resource not found"),
    ]
    
    for error in errors:
        category = error._determine_category()
        severity = error._determine_severity()
        
        print(f"✅ {error.__class__.__name__}:")
        print(f"   Category: {category.value}")
        print(f"   Severity: {severity.value}")
        print(f"   Message: {error.message}")


def demo_create_method():
    """Demonstrate the create class method."""
    print("\n🎨 Create Method Demo")
    print("=" * 50)
    
    # Using create method for simple exceptions
    simple_error = MindFlowError.create(
        "Simple error",
        component="test_component",
        user_id="user123",
        operation="test_operation"
    )
    
    print(f"✅ Created error with create method:")
    print(f"   Message: {simple_error.message}")
    print(f"   Component: {simple_error.component}")
    print(f"   User ID: {simple_error.user_id}")
    print(f"   Context: {simple_error.context}")


async def main():
    """Run all demos."""
    print("🚀 Enhanced Exceptions System Demo")
    print("=" * 60)
    print("Demonstrating fluent interfaces, builder patterns,")
    print("schema conversion, and enhanced error handling.")
    print("=" * 60)
    
    demo_fluent_interfaces()
    demo_builder_patterns()
    demo_templates()
    demo_schema_conversion()
    demo_user_friendly_responses()
    await demo_error_context()
    demo_category_and_severity()
    demo_create_method()
    
    print("\n🎉 Demo Complete!")
    print("All enhanced exception features demonstrated successfully.")


if __name__ == "__main__":
    asyncio.run(main())
