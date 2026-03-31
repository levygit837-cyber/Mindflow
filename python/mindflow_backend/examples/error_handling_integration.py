"""Example of integrating error handling into MindFlow applications.

Shows how to set up error handling middleware, use decorators,
and implement consistent error handling patterns using OmniMind's
comprehensive error handling system.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mindflow_backend.utils.error_handling import (
    CircuitBreaker,
    ErrorContext,
    handle_errors,
    retry_on_error,
)

# Use OmniMind's error handling utilities
from mindflow_backend.utils.error_setup import (
    setup_comprehensive_error_handling,
    setup_fastapi_error_handling,
)


def setup_fastapi_error_handling_legacy(app: FastAPI, debug: bool = False) -> None:
    """Legacy setup function - use setup_fastapi_error_handling from utils instead."""
    
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


def setup_grpc_error_handling_legacy(server, debug: bool = False) -> None:
    """Legacy setup function - use setup_grpc_error_handling from utils instead."""
    
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
    """Create example FastAPI app with error handling using OmniMind utilities."""
    
    app = FastAPI(title="MindFlow Example API")
    
    # Set up error handling using OmniMind utilities
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


def create_comprehensive_app() -> tuple[FastAPI, dict]:
    """Create comprehensive app with both FastAPI and gRPC error handling."""
    
    # Create FastAPI app
    app = FastAPI(title="MindFlow Comprehensive Example")
    
    # Import gRPC server for demonstration
    import grpc
    grpc_server = grpc.server(None)
    
    # Set up comprehensive error handling
    setup_status = setup_comprehensive_error_handling(
        fastapi_app=app,
        grpc_server=grpc_server,
        debug=True,
        fastapi_cors_origins=["http://localhost:3000"],
        grpc_port=50051,
    )
    
    return app, setup_status


if __name__ == "__main__":
    # Example usage
    app = create_example_app()
    
    print("=== MindFlow Error Handling Integration Example ===")
    print("Features demonstrated:")
    print("- FastAPI app with error handling middleware")
    print("- Service class with error handling decorators")
    print("- Circuit breaker protection")
    print("- Error context tracking")
    print("- Comprehensive setup utilities")
    print("\nTo run the basic example:")
    print("  uvicorn examples.error_handling_integration:create_example_app --reload")
    print("\nTo run the comprehensive example:")
    print("  uvicorn examples.error_handling_integration:create_comprehensive_app --reload")
    print("\nFor a complete service example:")
    print("  uvicorn examples.service_with_error_handling:create_fastapi_app_with_service --reload")
    
    # Demonstrate comprehensive setup
    print("\n=== Comprehensive Setup Demo ===")
    comprehensive_app, setup_status = create_comprehensive_app()
    print(f"FastAPI setup: {setup_status['fastapi_setup']}")
    print(f"gRPC setup: {setup_status['grpc_setup']}")
    print(f"Debug mode: {setup_status['debug_enabled']}")
    print("Configuration:", setup_status['configuration'])
