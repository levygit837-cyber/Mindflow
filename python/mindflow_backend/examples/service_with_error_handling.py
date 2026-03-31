"""Example service demonstrating comprehensive error handling patterns.

Shows how to use MindFlow's error handling utilities in a real service
with proper integration of decorators, context managers, and custom exceptions.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mindflow_backend.exceptions import (
    AuthenticationError,
    NetworkError,
    ResourceError,
    TimeoutError,
    ValidationError,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.utils.error_handling import (
    CircuitBreaker,
    ErrorContext,
    handle_errors,
    retry_on_error,
)

_logger = get_logger(__name__)


class ExampleService:
    """Example service demonstrating error handling patterns."""
    
    def __init__(self, service_name: str = "ExampleService"):
        self.service_name = service_name
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=NetworkError,
        )
    
    @handle_errors(
        error_type=ValidationError,
        default_return=None,
        log_error=True,
        reraise=False,
        error_message="Data validation failed during processing"
    )
    def process_user_data(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Process user data with validation error handling."""
        if not data.get("user_id"):
            raise ValidationError("Missing user_id field")
        
        if not data.get("email"):
            raise ValidationError("Missing email field")
        
        # Simulate processing
        processed_data = {
            "user_id": data["user_id"],
            "email": data["email"],
            "processed": True,
            "service": self.service_name,
        }
        
        _logger.info(
            "user_data_processed",
            user_id=data["user_id"],
            service=self.service_name,
        )
        
        return processed_data
    
    @retry_on_error(
        max_attempts=3,
        delay=1.0,
        backoff_factor=2.0,
        exceptions=(NetworkError, TimeoutError),
        log_attempts=True,
    )
    @handle_errors(
        error_type=NetworkError,
        default_return={"status": "offline", "data": None},
        log_error=True,
        reraise=False,
    )
    def fetch_external_api_data(self, endpoint: str, timeout: float = 10.0) -> dict[str, Any]:
        """Fetch data from external API with retry logic and error handling."""
        import random

        import requests
        
        # Simulate network failures for demonstration
        if random.random() < 0.3:  # 30% failure rate
            raise NetworkError(
                f"Failed to connect to {endpoint}",
                endpoint=endpoint,
                timeout=timeout,
            )
        
        try:
            response = requests.get(endpoint, timeout=timeout)
            response.raise_for_status()
            
            _logger.info(
                "external_api_success",
                endpoint=endpoint,
                status_code=response.status_code,
            )
            
            return {
                "status": "success",
                "data": response.json(),
                "endpoint": endpoint,
            }
            
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Request to {endpoint} timed out after {timeout}s",
                operation="fetch_external_api_data",
                timeout_seconds=timeout,
            )
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(
                f"Connection failed to {endpoint}: {e}",
                endpoint=endpoint,
            )
    
    @CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    @handle_errors(
        error_type=ResourceError,
        default_return={"status": "degraded", "message": "Service temporarily unavailable"},
        log_error=True,
        reraise=False,
    )
    def perform_critical_operation(self, resource_id: str) -> dict[str, Any]:
        """Perform critical operation with circuit breaker protection."""
        import random
        
        # Simulate resource exhaustion
        if random.random() < 0.4:  # 40% failure rate
            raise ResourceError(
                f"Resource {resource_id} is exhausted",
                resource_type="database_connection",
                current_usage="95%",
            )
        
        # Simulate successful operation
        result = {
            "status": "success",
            "resource_id": resource_id,
            "operation": "critical_processing",
            "timestamp": asyncio.get_event_loop().time(),
        }
        
        _logger.info(
            "critical_operation_success",
            resource_id=resource_id,
            service=self.service_name,
        )
        
        return result
    
    def complex_workflow(
        self,
        user_id: str,
        session_id: str,
        workflow_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Complex workflow demonstrating error context tracking."""
        with ErrorContext(
            operation="complex_workflow",
            component=self.service_name,
            user_id=user_id,
            session_id=session_id,
            metadata={
                "workflow_type": "user_processing",
                "steps": ["validation", "external_fetch", "critical_op"],
                "version": "1.0",
            },
        ) as ctx:
            try:
                # Step 1: Validate and process user data
                ctx.record_steps("validation")
                processed_data = self.process_user_data(workflow_data)
                if processed_data is None:
                    ctx.record_error(ValidationError("User data processing failed"))
                    return {"status": "failed", "step": "validation"}
                
                # Step 2: Fetch external data
                ctx.record_steps("external_fetch")
                external_data = self.fetch_external_api_data(
                    f"https://api.example.com/users/{user_id}"
                )
                
                # Step 3: Perform critical operation
                ctx.record_steps("critical_op")
                critical_result = self.perform_critical_operation(
                    f"resource_{user_id}"
                )
                
                # Combine results
                final_result = {
                    "status": "success",
                    "user_data": processed_data,
                    "external_data": external_data,
                    "critical_result": critical_result,
                    "workflow_id": ctx.operation_id,
                }
                
                _logger.info(
                    "complex_workflow_completed",
                    user_id=user_id,
                    session_id=session_id,
                    workflow_id=ctx.operation_id,
                )
                
                return final_result
                
            except Exception as e:
                ctx.record_error(e)
                _logger.error(
                    "complex_workflow_failed",
                    user_id=user_id,
                    session_id=session_id,
                    error=str(e),
                    error_type=e.__class__.__name__,
                )
                raise
    
    async def async_operation_with_timeout(self, data: dict[str, Any]) -> dict[str, Any]:
        """Async operation with timeout handling."""
        from mindflow_backend.utils.error_handling import timeout_handler
        
        @timeout_handler(timeout_seconds=5.0, timeout_message="Operation timed out")
        async def slow_operation():
            await asyncio.sleep(2)  # Simulate slow operation
            return {"processed": True, "data": data}
        
        try:
            return await slow_operation()
        except TimeoutError:
            _logger.error(
                "async_operation_timeout",
                operation="slow_operation",
                timeout_seconds=5.0,
            )
            raise
    
    def authenticate_user(self, credentials: dict[str, str]) -> dict[str, Any]:
        """User authentication with comprehensive error handling."""
        @handle_errors(
            error_type=AuthenticationError,
            default_return={"authenticated": False, "reason": "invalid_credentials"},
            log_error=True,
            reraise=False,
        )
        def _authenticate():
            username = credentials.get("username")
            password = credentials.get("password")
            
            if not username or not password:
                raise AuthenticationError("Missing username or password")
            
            # Simulate authentication logic
            if username == "admin" and password == "secret":
                return {
                    "authenticated": True,
                    "user_id": "admin_123",
                    "role": "administrator",
                }
            else:
                raise AuthenticationError(
                    "Invalid credentials",
                    user_id=username,
                )
        
        return _authenticate()


# Example usage functions
def create_fastapi_app_with_service() -> Any:
    """Create FastAPI app with integrated service and error handling."""
    from fastapi import FastAPI

    from mindflow_backend.utils.error_setup import setup_fastapi_error_handling
    
    app = FastAPI(title="MindFlow Example API")
    
    # Set up error handling
    setup_fastapi_error_handling(app, debug=True)
    
    service = ExampleService()
    
    @app.post("/process")
    async def process_endpoint(data: dict[str, Any]) -> dict[str, Any]:
        """Process user data endpoint."""
        return service.process_user_data(data)
    
    @app.get("/external/{user_id}")
    async def external_endpoint(user_id: str) -> dict[str, Any]:
        """Fetch external data endpoint."""
        return service.fetch_external_api_data(f"https://api.example.com/users/{user_id}")
    
    @app.post("/critical/{resource_id}")
    async def critical_endpoint(resource_id: str) -> dict[str, Any]:
        """Critical operation endpoint."""
        return service.perform_critical_operation(resource_id)
    
    @app.post("/workflow")
    async def workflow_endpoint(
        user_id: str,
        session_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Complex workflow endpoint."""
        return service.complex_workflow(user_id, session_id, data)
    
    @app.post("/auth")
    async def auth_endpoint(credentials: dict[str, str]) -> dict[str, Any]:
        """Authentication endpoint."""
        return service.authenticate_user(credentials)
    
    return app


def create_grpc_server_with_service() -> Any:
    """Create gRPC server with integrated service and error handling."""
    import grpc
    from mindflow_backend.utils.error_setup import setup_grpc_error_handling
    
    server = grpc.server(None)
    
    # Set up error handling
    setup_grpc_error_handling(server, debug=True, port=50051)
    
    # Add gRPC services here
    # server.add_insecure_port('[::]:50051')
    
    return server


if __name__ == "__main__":
    # Demonstration of service usage
    service = ExampleService()
    
    print("=== MindFlow Error Handling Service Demo ===")
    
    # Test validation error handling
    print("\n1. Testing validation error handling:")
    result = service.process_user_data({"invalid": "data"})
    print(f"Result: {result}")
    
    # Test successful processing
    print("\n2. Testing successful processing:")
    result = service.process_user_data({
        "user_id": "user_123",
        "email": "user@example.com",
    })
    print(f"Result: {result}")
    
    # Test external API with retry
    print("\n3. Testing external API with retry:")
    result = service.fetch_external_api_data("https://httpbin.org/json")
    print(f"Result: {result}")
    
    # Test circuit breaker
    print("\n4. Testing circuit breaker:")
    for i in range(5):
        result = service.perform_critical_operation(f"resource_{i}")
        print(f"Attempt {i+1}: {result['status']}")
    
    # Test complex workflow
    print("\n5. Testing complex workflow:")
    try:
        result = service.complex_workflow(
            user_id="user_123",
            session_id="session_456",
            workflow_data={"user_id": "user_123", "email": "test@example.com"},
        )
        print(f"Workflow result: {result['status']}")
    except Exception as e:
        print(f"Workflow failed: {e}")
    
    print("\n=== Demo Complete ===")
    print("To run FastAPI app:")
    print("  uvicorn mindflow_backend.examples.service_with_error_handling:create_fastapi_app_with_service --reload")
