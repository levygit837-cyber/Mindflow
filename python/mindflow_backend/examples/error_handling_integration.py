"""Example of integrating error handling into MindFlow applications.

Shows how to set up error handling middleware, use decorators,
and implement consistent error handling patterns.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mindflow_backend.api.middleware import ErrorHandlerMiddleware
from mindflow_backend.grpc.interceptors import ErrorHandlerInterceptor
from mindflow_backend.utils.error_handling import (
    handle_errors,
    retry_on_error,
    ErrorContext,
    CircuitBreaker,
)


def setup_fastapi_error_handling(app: FastAPI, debug: bool = False) -> None:
    """Set up error handling for FastAPI application."""
    
    # Add error handling middleware
    app.add_middleware(ErrorHandlerMiddleware, debug=debug)
    
    # Add other middleware as needed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_grpc_error_handling(server, debug: bool = False) -> None:
    """Set up error handling for gRPC server."""
    
    # Add error handling interceptor
    error_interceptor = ErrorHandlerInterceptor(debug=debug)
    server.add_insecure_port("[::]:50051")  # Example port
    server.add_interceptor(error_interceptor)


# Example usage in service classes
class ExampleService:
    """Example service showing error handling patterns."""
    
    @handle_errors(
        error_type=ValueError,
        default_return=None,
        log_error=True,
        reraise=False,
        error_message="Processing failed due to invalid input"
    )
    def process_data(self, data: dict) -> dict | None:
        """Process data with error handling."""
        if not data.get("required_field"):
            raise ValueError("Missing required field")
        
        # Process data...
        return {"processed": True, "data": data}
    
    @retry_on_error(
        max_attempts=3,
        delay=1.0,
        backoff_factor=2.0,
        exceptions=(ConnectionError, TimeoutError),
        log_attempts=True,
    )
    def fetch_external_data(self, url: str) -> dict:
        """Fetch external data with retry logic."""
        # Simulate external API call
        import requests
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    
    @CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
    def unreliable_operation(self) -> str:
        """Operation with circuit breaker protection."""
        # Simulate unreliable operation
        import random
        
        if random.random() < 0.3:  # 30% failure rate
            raise ConnectionError("Service unavailable")
        
        return "Operation successful"
    
    def complex_operation(self, user_id: str, session_id: str) -> dict:
        """Complex operation with error context tracking."""
        with ErrorContext(
            operation="complex_operation",
            component="example_service",
            user_id=user_id,
            session_id=session_id,
            metadata={"version": "1.0"},
        ) as ctx:
            try:
                # Step 1: Process data
                processed = self.process_data({"input": "test"})
                if processed is None:
                    ctx.record_error(ValueError("Data processing failed"))
                
                # Step 2: Fetch external data
                external = self.fetch_external_data("https://api.example.com/data")
                
                # Step 3: Perform unreliable operation
                result = self.unreliable_operation()
                
                return {
                    "processed": processed,
                    "external": external,
                    "result": result,
                }
                
            except Exception as e:
                ctx.record_error(e)
                raise


# Example FastAPI route with error handling
def create_example_app() -> FastAPI:
    """Create example FastAPI app with error handling."""
    
    app = FastAPI(title="MindFlow Example API")
    
    # Set up error handling
    setup_fastapi_error_handling(app, debug=True)
    
    service = ExampleService()
    
    @app.post("/process")
    async def process_endpoint(data: dict) -> dict:
        """Example endpoint with automatic error handling."""
        # Error handling is done by middleware
        return service.process_data(data)
    
    @app.get("/external/{url}")
    async def external_endpoint(url: str) -> dict:
        """Example endpoint with retry logic."""
        return service.fetch_external_data(f"https://{url}")
    
    @app.get("/unreliable")
    async def unreliable_endpoint() -> str:
        """Example endpoint with circuit breaker."""
        return service.unreliable_operation()
    
    @app.post("/complex")
    async def complex_endpoint(user_id: str, session_id: str, data: dict) -> dict:
        """Example endpoint with error context tracking."""
        return service.complex_operation(user_id, session_id)
    
    return app


if __name__ == "__main__":
    # Example usage
    app = create_example_app()
    
    print("Error handling integration example:")
    print("- FastAPI app with error handling middleware")
    print("- Service class with error handling decorators")
    print("- Circuit breaker protection")
    print("- Error context tracking")
    print("\nTo run the example:")
    print("  uvicorn examples.error_handling_integration:create_example_app --reload")
