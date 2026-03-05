# OmniMind Error Handling Guide

This guide provides comprehensive documentation for the OmniMind error handling system, including usage patterns, best practices, and integration examples.

## Table of Contents

1. [Overview](#overview)
2. [Error Architecture](#error-architecture)
3. [Base Exceptions](#base-exceptions)
4. [Error Categories](#error-categories)
5. [Error Schemas](#error-schemas)
6. [Middleware Integration](#middleware-integration)
7. [Utility Functions](#utility-functions)
8. [Best Practices](#best-practices)
9. [Examples](#examples)
10. [Troubleshooting](#troubleshooting)

## Overview

The OmniMind error handling system provides:

- **Structured Exception Hierarchy**: Organized exception classes for different error types
- **Standardized Error Schemas**: Consistent error response formats
- **Automatic Error Handling**: Middleware for FastAPI and gRPC
- **Utility Functions**: Decorators and context managers for common patterns
- **Observability**: Structured logging and error tracking

### Key Benefits

1. **Consistency**: All errors follow the same structure and format
2. **Debuggability**: Rich context and metadata for troubleshooting
3. **User Experience**: User-friendly error messages
4. **Resilience**: Built-in retry and circuit breaker patterns
5. **Monitoring**: Structured logging for observability

## Error Architecture

```
OmniMindError (Base)
├── SystemError
│   ├── ConfigurationError
│   ├── InfrastructureError
│   ├── NetworkError
│   ├── ResourceError
│   └── TimeoutError
└── BusinessLogicError
    ├── ValidationError
    ├── AuthenticationError
    ├── AuthorizationError
    ├── BusinessRuleError
    ├── WorkflowError
    ├── DomainError
    ├── ConflictError
    └── NotFoundError
```

### Domain-Specific Exceptions

- **Agent Errors**: `AgentExecutionError`, `AgentTimeoutError`, `ContextRetrievalError`
- **Provider Errors**: `ProviderError`, `RateLimitError`, `TokenLimitError`
- **Orchestrator Errors**: `DecompositionError`, `SchedulingError`, `GraphExecutionError`
- **Storage Errors**: `DatabaseError`, `VectorStoreError`, `CacheError`
- **API Errors**: `RequestValidationError`, `StreamingError`, `RoutingError`

## Base Exceptions

### OmniMindError

The base exception for all OmniMind system errors.

```python
from omnimind_backend.exceptions import OmniMindError

try:
    # Some operation that might fail
    pass
except Exception as exc:
    raise OmniMindError(
        message="Operation failed",
        component="my_component",
        session_id="session_123",
        context={"user_action": "create_item"},
        cause=exc
    )
```

**Properties:**
- `error_id`: Unique identifier for tracking
- `component`: Component where error occurred
- `session_id`: User session identifier
- `context`: Additional metadata
- `timestamp`: When error occurred
- `cause`: Original exception

### SystemError

For infrastructure and operational errors.

```python
from omnimind_backend.exceptions import SystemError

raise SystemError(
    message="Database connection failed",
    service="postgresql",
    operation="connect",
    severity="high",
    recoverable=True
)
```

### BusinessLogicError

For expected business logic errors.

```python
from omnimind_backend.exceptions import BusinessLogicError

raise BusinessLogicError(
    message="Invalid input data",
    user_message="Please check your input and try again",
    error_code="VALIDATION_001",
    recoverable=True
)
```

## Error Categories

Errors are categorized for routing and handling:

| Category | Description | HTTP Status |
|----------|-------------|-------------|
| `VALIDATION` | Input validation errors | 400 |
| `AUTHENTICATION` | Authentication failures | 401 |
| `AUTHORIZATION` | Permission denied | 403 |
| `NOT_FOUND` | Resource not found | 404 |
| `CONFLICT` | Resource conflicts | 409 |
| `RATE_LIMIT` | Too many requests | 429 |
| `NETWORK` | Network connectivity | 503 |
| `TIMEOUT` | Operation timeouts | 504 |
| `RESOURCE` | Resource exhaustion | 503 |
| `INFRASTRUCTURE` | System failures | 503 |
| `SYSTEM` | Internal errors | 500 |

## Error Schemas

### ErrorSchema

Universal schema for all error responses:

```python
from omnimind_backend.schemas.errors import ErrorSchema, ErrorCategory, ErrorSeverity

error = ErrorSchema(
    error_id="err_123",
    error_type="ValidationError",
    error_code="VALIDATION_001",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.LOW,
    message="Invalid input data",
    user_message="Please check your input",
    component="api",
    recoverable=True
)
```

### Creating Errors from Exceptions

```python
from omnimind_backend.exceptions import ValidationError
from omnimind_backend.schemas.errors import ErrorSchema, ErrorCategory, ErrorSeverity

try:
    # Some validation logic
    raise ValidationError("Invalid email format", field="email")
except ValidationError as exc:
    error_schema = ErrorSchema.from_exception(
        exc,
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        error_code="VALIDATION_001",
        component="api"
    )
```

## Middleware Integration

### FastAPI Setup

```python
from fastapi import FastAPI
from omnimind_backend.api.middleware import ErrorHandlerMiddleware

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware, debug=True)

@app.get("/example")
async def example_endpoint():
    # Errors are automatically handled by middleware
    raise ValidationError("Invalid input")
```

### gRPC Setup

```python
import grpc
from omnimind_backend.grpc.interceptors import ErrorHandlerInterceptor

server = grpc.server(None)
error_interceptor = ErrorHandlerInterceptor(debug=True)
server.add_interceptor(error_interceptor)
```

## Utility Functions

### Error Handling Decorator

```python
from omnimind_backend.utils.error_handling import handle_errors

@handle_errors(
    error_type=ValueError,
    default_return=None,
    log_error=True,
    reraise=False
)
def process_data(data: dict) -> dict:
    if not data.get("required_field"):
        raise ValueError("Missing required field")
    return {"processed": True}
```

### Retry Decorator

```python
from omnimind_backend.utils.error_handling import retry_on_error

@retry_on_error(
    max_attempts=3,
    delay=1.0,
    backoff_factor=2.0,
    exceptions=(ConnectionError, TimeoutError)
)
def fetch_external_data(url: str) -> dict:
    # External API call that might fail
    pass
```

### Circuit Breaker

```python
from omnimind_backend.utils.error_handling import CircuitBreaker

@CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
def unreliable_operation() -> str:
    # Operation that might fail frequently
    pass
```

### Error Context

```python
from omnimind_backend.utils.error_handling import ErrorContext

def complex_operation(user_id: str, session_id: str) -> dict:
    with ErrorContext(
        operation="complex_operation",
        component="my_service",
        user_id=user_id,
        session_id=session_id
    ) as ctx:
        try:
            # Operation logic
            result = process_data()
            return result
        except Exception as e:
            ctx.record_error(e)
            raise
```

## Best Practices

### 1. Use Specific Exceptions

```python
# Good
from omnimind_backend.exceptions import ValidationError

if not email or "@" not in email:
    raise ValidationError("Invalid email format", field="email")

# Avoid
raise Exception("Bad email")
```

### 2. Provide Context

```python
# Good
raise ValidationError(
    "Invalid email format",
    field="email",
    value=email,
    validation_rule="email_format"
)

# Avoid
raise ValidationError("Invalid email")
```

### 3. Use User-Friendly Messages

```python
# Good
raise ValidationError(
    "Email format is invalid",
    user_message="Please enter a valid email address (e.g., user@example.com)"
)

# Avoid
raise ValidationError("email_validation_failed_pattern_mismatch")
```

### 4. Log Appropriately

```python
# Good - middleware handles logging automatically
raise ValidationError("Invalid input")

# For manual logging with context
from omnimind_backend.utils.error_handling import ErrorContext

with ErrorContext(operation="user_registration", user_id=user_id):
    # Operation that might fail
    pass
```

### 5. Handle Recoverable Errors

```python
# Good - use retry for transient failures
@retry_on_error(max_attempts=3, exceptions=(ConnectionError,))
def fetch_data():
    pass

# Good - use circuit breaker for unreliable services
@CircuitBreaker(failure_threshold=5)
def external_service_call():
    pass
```

## Examples

### Complete Service Example

```python
from omnimind_backend.exceptions import (
    ValidationError, 
    DatabaseError,
    ProviderError
)
from omnimind_backend.utils.error_handling import (
    handle_errors,
    retry_on_error,
    ErrorContext
)

class UserService:
    @handle_errors(error_type=ValidationError, default_return=None)
    def create_user(self, user_data: dict) -> dict:
        """Create a new user with validation."""
        if not user_data.get("email"):
            raise ValidationError("Email is required", field="email")
        
        if not user_data.get("password"):
            raise ValidationError("Password is required", field="password")
        
        return self._save_user(user_data)
    
    @retry_on_error(max_attempts=3, exceptions=(DatabaseError,))
    def _save_user(self, user_data: dict) -> dict:
        """Save user to database with retry logic."""
        # Database operation that might fail
        pass
    
    def get_user_profile(self, user_id: str, session_id: str) -> dict:
        """Get user profile with error tracking."""
        with ErrorContext(
            operation="get_user_profile",
            component="user_service",
            user_id=user_id,
            session_id=session_id
        ):
            user = self.fetch_user(user_id)
            profile = self.enrich_profile(user)
            return profile
    
    @retry_on_error(exceptions=(ProviderError,))
    def enrich_profile(self, user: dict) -> dict:
        """Enrich profile using external provider."""
        # External API call
        pass
```

### API Endpoint Example

```python
from fastapi import FastAPI, HTTPException
from omnimind_backend.exceptions import ValidationError
from omnimind_backend.schemas.errors import ErrorResponse

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware, debug=True)

@app.post("/users")
async def create_user(user_data: dict):
    """Create user endpoint - errors handled by middleware."""
    service = UserService()
    return service.create_user(user_data)

# Manual error handling if needed
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        service = UserService()
        return service.get_user_profile(user_id, "session_123")
    except ValidationError as exc:
        # Convert to HTTP exception for specific handling
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(error=ErrorSchema.from_exception(
                exc,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                error_code="VALIDATION_001",
                component="api"
            )).model_dump()
        )
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all exception modules are properly imported
2. **Middleware Not Working**: Ensure middleware is added before other middleware
3. **Error Context Missing**: Check that ErrorContext is used as a context manager
4. **Retry Not Working**: Verify exception types match the retry configuration

### Debug Mode

Enable debug mode for more detailed error information:

```python
# FastAPI
app.add_middleware(ErrorHandlerMiddleware, debug=True)

# gRPC
error_interceptor = ErrorHandlerInterceptor(debug=True)
```

### Error Tracking

Use error IDs for tracking:

```python
try:
    # Operation
    pass
except OmniMindError as exc:
    # Log error_id for customer support
    print(f"Error ID: {exc.error_id}")
    raise
```

### Monitoring

Monitor error rates and patterns:

```python
# Check logs for structured error data
# Look for:
# - error_id
# - error_code  
# - category
# - severity
# - component
```

## Migration Guide

### From Generic Exceptions

```python
# Before
try:
    validate_input(data)
except Exception as e:
    return {"error": str(e)}

# After
from omnimind_backend.exceptions import ValidationError

try:
    validate_input(data)
except ValidationError as e:
    # Middleware handles response formatting
    raise
```

### Adding Error Handling to Existing Code

1. Import appropriate exceptions
2. Replace generic exceptions with specific ones
3. Add error context where needed
4. Add retry/circuit breaker for external calls
5. Enable error handling middleware

This error handling system provides a robust foundation for building resilient applications in OmniMind.
