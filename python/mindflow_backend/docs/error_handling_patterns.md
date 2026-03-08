# Error Handling Patterns Guide

This guide demonstrates the recommended patterns for using OmniMind's comprehensive error handling system.

## Quick Start

### 1. Basic Setup for FastAPI

```python
from fastapi import FastAPI
from mindflow_backend.utils.error_setup import setup_fastapi_error_handling

app = FastAPI()
setup_fastapi_error_handling(app, debug=True)
```

### 2. Basic Setup for gRPC

```python
import grpc
from mindflow_backend.utils.error_setup import setup_grpc_error_handling

server = grpc.server(None)
setup_grpc_error_handling(server, debug=True, port=50051)
```

### 3. Comprehensive Setup

```python
from mindflow_backend.utils.error_setup import setup_comprehensive_error_handling

setup_status = setup_comprehensive_error_handling(
    fastapi_app=app,
    grpc_server=server,
    debug=True,
    fastapi_cors_origins=["http://localhost:3000"],
    grpc_port=50051,
)
```

## Error Handling Patterns

### Pattern 1: Service Method with Validation

```python
from mindflow_backend.exceptions import ValidationError
from mindflow_backend.utils.error_handling import handle_errors

class UserService:
    @handle_errors(
        error_type=ValidationError,
        default_return=None,
        log_error=True,
        reraise=False,
        error_message="User data validation failed"
    )
    def create_user(self, data: dict) -> dict | None:
        if not data.get("email"):
            raise ValidationError("Email is required")
        
        # Process user creation
        return {"id": "123", "email": data["email"]}
```

### Pattern 2: External API with Retry Logic

```python
from mindflow_backend.exceptions import NetworkError, TimeoutError
from mindflow_backend.utils.error_handling import retry_on_error

class ExternalAPIService:
    @retry_on_error(
        max_attempts=3,
        delay=1.0,
        backoff_factor=2.0,
        exceptions=(NetworkError, TimeoutError),
        log_attempts=True,
    )
    def fetch_data(self, endpoint: str) -> dict:
        # Make API call
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        return response.json()
```

### Pattern 3: Circuit Breaker for Unstable Operations

```python
from mindflow_backend.utils.error_handling import CircuitBreaker

class DatabaseService:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=ConnectionError,
        )
    
    @CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    def execute_query(self, query: str) -> list:
        # Execute database query
        return db.execute(query)
```

### Pattern 4: Complex Workflow with Context Tracking

```python
from mindflow_backend.utils.error_handling import ErrorContext

class WorkflowService:
    def process_order(self, user_id: str, order_data: dict) -> dict:
        with ErrorContext(
            operation="process_order",
            component="workflow_service",
            user_id=user_id,
            metadata={"order_type": order_data.get("type")},
        ) as ctx:
            try:
                # Step 1: Validate order
                validated = self.validate_order(order_data)
                ctx.record_steps("validation")
                
                # Step 2: Process payment
                payment_result = self.process_payment(validated)
                ctx.record_steps("payment")
                
                # Step 3: Update inventory
                inventory = self.update_inventory(validated)
                ctx.record_steps("inventory")
                
                return {
                    "status": "completed",
                    "payment": payment_result,
                    "inventory": inventory,
                }
                
            except Exception as e:
                ctx.record_error(e)
                raise
```

### Pattern 5: Async Operations with Timeout

```python
from mindflow_backend.utils.error_handling import timeout_handler

class AsyncService:
    @timeout_handler(timeout_seconds=5.0)
    async def slow_operation(self, data: dict) -> dict:
        await asyncio.sleep(2)  # Simulate work
        return {"processed": True, "data": data}
```

## Custom Exception Patterns

### Pattern 1: Domain-Specific Exceptions

```python
from mindflow_backend.exceptions import MindFlowError, BusinessLogicError

class InsufficientInventoryError(BusinessLogicError):
    def __init__(self, product_id: str, requested: int, available: int):
        super().__init__(
            f"Insufficient inventory for product {product_id}",
            product_id=product_id,
            requested=requested,
            available=available,
        )
        self.product_id = product_id
        self.requested = requested
        self.available = available
```

### Pattern 2: Context-Rich Exceptions

```python
class PaymentProcessingError(MindFlowError):
    def __init__(self, message: str, payment_id: str, amount: float, **kwargs):
        super().__init__(
            message,
            component="payment_service",
            context={
                "payment_id": payment_id,
                "amount": amount,
                "currency": "USD",
            },
            **kwargs,
        )
```

## Middleware Integration Patterns

### Pattern 1: Custom Middleware

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class CustomMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            # Record success metrics
            return response
        except Exception as e:
            # Record error metrics
            self.record_error_metrics(e, request)
            raise
```

## Testing Error Handling

### Pattern 1: Unit Test for Exception Handling

```python
import pytest
from mindflow_backend.exceptions import ValidationError

def test_user_validation_error():
    service = UserService()
    
    # Test validation failure
    result = service.create_user({"invalid": "data"})
    assert result is None
    
    # Test validation success
    result = service.create_user({"email": "test@example.com"})
    assert result["email"] == "test@example.com"
```

### Pattern 2: Integration Test for Error Context

```python
def test_workflow_error_context():
    service = WorkflowService()
    
    with pytest.raises(ValidationError):
        service.process_order("user_123", {"invalid": "order"})
    
    # Verify error context was logged
    # Check logs for error tracking
```

## Best Practices

### 1. Use Specific Exception Types
- Prefer specific exceptions over generic `Exception`
- Create domain-specific exceptions for business logic
- Use appropriate base classes (`BusinessLogicError`, `SystemError`)

### 2. Provide Context
- Always include relevant context (user_id, session_id, operation)
- Use structured context data for debugging
- Include component identification

### 3. Handle Errors Appropriately
- Use `@handle_errors` for expected failures
- Use retry logic for transient failures
- Use circuit breakers for unstable dependencies

### 4. Log Structured Information
- Use structured logging with key-value pairs
- Include error_id for correlation
- Log at appropriate levels based on severity

### 5. Configure Error Handling
- Use setup utilities for consistent configuration
- Enable debug mode in development only
- Configure appropriate timeouts and retry limits

## Configuration Examples

### Development Configuration

```python
from mindflow_backend.utils.error_setup import create_error_handling_config

dev_config = create_error_handling_config(
    debug=True,
    log_level="DEBUG",
    enable_metrics=False,
    enable_tracing=False,
)
```

### Production Configuration

```python
prod_config = create_error_handling_config(
    debug=False,
    log_level="INFO",
    enable_metrics=True,
    enable_tracing=True,
)
```

## Migration Guide

### From Basic Exception Handling

**Before:**
```python
def process_data(data):
    try:
        # Processing logic
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None
```

**After:**
```python
@handle_errors(
    error_type=ValidationError,
    default_return=None,
    log_error=True,
    error_message="Data processing failed"
)
def process_data(data):
    # Processing logic
    return result
```

### From Manual Retry Logic

**Before:**
```python
def fetch_with_retry(url):
    for attempt in range(3):
        try:
            return requests.get(url)
        except:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
```

**After:**
```python
@retry_on_error(max_attempts=3, delay=1.0, backoff_factor=2.0)
def fetch_with_retry(url):
    return requests.get(url)
```

## Troubleshooting

### Common Issues

1. **Circular Imports**: Import exceptions inside functions to avoid circular dependencies
2. **Missing Context**: Always provide user_id and session_id when available
3. **Incorrect Exception Types**: Use appropriate base exceptions for proper classification
4. **Over-Retrying**: Set appropriate retry limits for non-transient errors

### Debug Mode

Enable debug mode to get detailed error information:

```python
setup_fastapi_error_handling(app, debug=True)
```

This will include stack traces and technical details in error responses.
