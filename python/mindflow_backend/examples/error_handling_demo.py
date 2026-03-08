#!/usr/bin/env python3
"""Comprehensive error handling demonstration for OmniMind.

This script demonstrates all the error handling features and improvements
implemented to address the gaps identified in the error handling system.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

# Add the project root to the path
import pathlib
project_root = str(pathlib.Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from fastapi import FastAPI
import grpc

from mindflow_backend.utils.error_setup import (
    setup_fastapi_error_handling,
    setup_grpc_error_handling,
    setup_comprehensive_error_handling,
    create_error_handling_config,
)
from mindflow_backend.utils.error_handling import (
    handle_errors,
    retry_on_error,
    ErrorContext,
    CircuitBreaker,
)
from mindflow_backend.exceptions import (
    ValidationError,
    NetworkError,
    TimeoutError,
    ResourceError,
    MindFlowError,
)


class DemoService:
    """Demo service showcasing all error handling patterns."""
    
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5.0,
            expected_exception=NetworkError,
        )
    
    @handle_errors(
        error_type=ValidationError,
        default_return={"status": "validation_failed", "data": None},
        log_error=True,
        reraise=False,
        error_message="Input validation failed"
    )
    def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Demonstrate validation error handling."""
        if not data.get("required_field"):
            raise ValidationError("Missing required_field")
        
        return {"status": "valid", "data": data}
    
    @retry_on_error(
        max_attempts=3,
        delay=0.5,
        backoff_factor=2.0,
        exceptions=(NetworkError, TimeoutError),
        log_attempts=True,
    )
    def simulate_network_call(self, endpoint: str, should_fail: bool = False) -> dict[str, Any]:
        """Demonstrate retry logic with simulated network failures."""
        import random
        
        if should_fail and random.random() < 0.7:  # 70% failure rate
            raise NetworkError(f"Failed to connect to {endpoint}", endpoint=endpoint)
        
        return {"status": "success", "endpoint": endpoint, "data": "mock_data"}
    
    @CircuitBreaker(failure_threshold=2, recovery_timeout=3.0)
    def simulate_unstable_service(self, should_fail: bool = False) -> dict[str, Any]:
        """Demonstrate circuit breaker with unstable service."""
        if should_fail:
            raise ResourceError("Service temporarily unavailable", resource_type="database")
        
        return {"status": "success", "timestamp": asyncio.get_event_loop().time()}
    
    def complex_workflow(self, user_id: str, session_id: str) -> dict[str, Any]:
        """Demonstrate complex workflow with error context tracking."""
        with ErrorContext(
            operation="demo_workflow",
            component="DemoService",
            user_id=user_id,
            session_id=session_id,
            metadata={"demo": True, "version": "1.0"},
        ) as ctx:
            try:
                # Step 1: Validation
                ctx.record_steps("validation")
                valid_data = self.validate_input({"required_field": "test_value"})
                
                # Step 2: Network call
                ctx.record_steps("network_call")
                network_result = self.simulate_network_call("https://api.example.com")
                
                # Step 3: Unstable service
                ctx.record_steps("unstable_service")
                service_result = self.simulate_unstable_service()
                
                return {
                    "status": "workflow_completed",
                    "validation": valid_data,
                    "network": network_result,
                    "service": service_result,
                }
                
            except Exception as e:
                ctx.record_error(e)
                raise


def demo_setup_utilities():
    """Demonstrate error handling setup utilities."""
    print("=== Error Handling Setup Utilities Demo ===\n")
    
    # 1. Create configuration
    print("1. Creating error handling configuration:")
    config = create_error_handling_config(
        debug=True,
        log_level="DEBUG",
        enable_metrics=True,
        enable_tracing=False,
    )
    print(f"   Debug mode: {config['debug']}")
    print(f"   Log level: {config['log_level']}")
    print(f"   Metrics enabled: {config['enable_metrics']}")
    print(f"   Tracing enabled: {config['enable_tracing']}")
    print()
    
    # 2. FastAPI setup
    print("2. Setting up FastAPI error handling:")
    app = FastAPI(title="Demo API")
    setup_fastapi_error_handling(
        app,
        debug=True,
        cors_origins=["http://localhost:3000"],
        cors_allow_credentials=True,
    )
    print("   ✓ FastAPI error handling middleware added")
    print("   ✓ CORS middleware configured")
    print()
    
    # 3. gRPC setup
    print("3. Setting up gRPC error handling:")
    grpc_server = grpc.server(None)
    setup_grpc_error_handling(
        grpc_server,
        debug=True,
        port=50051,
        host="[::]:",
    )
    print("   ✓ gRPC error handling interceptor added")
    print("   ✓ Server configured for port 50051")
    print()
    
    # 4. Comprehensive setup
    print("4. Comprehensive setup for both FastAPI and gRPC:")
    setup_status = setup_comprehensive_error_handling(
        fastapi_app=app,
        grpc_server=grpc_server,
        debug=True,
        fastapi_cors_origins=["http://localhost:3000"],
        grpc_port=50052,
    )
    print(f"   FastAPI setup: {setup_status['fastapi_setup']}")
    print(f"   gRPC setup: {setup_status['grpc_setup']}")
    print(f"   Debug enabled: {setup_status['debug_enabled']}")
    print()
    
    return app, grpc_server


def demo_error_handling_patterns():
    """Demonstrate various error handling patterns."""
    print("=== Error Handling Patterns Demo ===\n")
    
    service = DemoService()
    
    # 1. Validation error handling
    print("1. Validation error handling:")
    result = service.validate_input({"invalid": "data"})
    print(f"   Invalid input result: {result}")
    
    result = service.validate_input({"required_field": "valid_value"})
    print(f"   Valid input result: {result}")
    print()
    
    # 2. Retry logic
    print("2. Retry logic with network failures:")
    try:
        result = service.simulate_network_call("https://api.example.com", should_fail=True)
        print(f"   Network call result: {result}")
    except Exception as e:
        print(f"   Network call failed after retries: {e}")
    print()
    
    # 3. Circuit breaker
    print("3. Circuit breaker pattern:")
    for i in range(4):
        try:
            result = service.simulate_unstable_service(should_fail=True)
            print(f"   Attempt {i+1}: {result['status']}")
        except Exception as e:
            print(f"   Attempt {i+1}: Failed - {e.__class__.__name__}")
    print()
    
    # 4. Complex workflow
    print("4. Complex workflow with error context:")
    try:
        result = service.complex_workflow(
            user_id="demo_user",
            session_id="demo_session",
        )
        print(f"   Workflow result: {result['status']}")
    except Exception as e:
        print(f"   Workflow failed: {e}")
    print()


def demo_custom_exceptions():
    """Demonstrate custom exception usage."""
    print("=== Custom Exceptions Demo ===\n")
    
    # 1. Basic custom exception
    print("1. Basic custom exception:")
    try:
        raise ValidationError("Invalid user data", field="email", value="invalid")
    except ValidationError as e:
        print(f"   Exception type: {e.__class__.__name__}")
        print(f"   Message: {e}")
        print(f"   Field: {getattr(e, 'field', 'N/A')}")
    print()
    
    # 2. Context-rich exception
    print("2. Context-rich exception:")
    try:
        raise MindFlowError(
            "Processing failed",
            component="DemoService",
            user_id="demo_user",
            session_id="demo_session",
            context={"operation": "demo", "step": "processing"},
        )
    except MindFlowError as e:
        print(f"   Error ID: {e.error_id}")
        print(f"   Component: {e.component}")
        print(f"   User ID: {e.user_id}")
        print(f"   Context: {e.context}")
    print()


def demo_fastapi_integration():
    """Demonstrate FastAPI integration."""
    print("=== FastAPI Integration Demo ===\n")
    
    app = FastAPI(title="Demo API")
    setup_fastapi_error_handling(app, debug=True)
    
    service = DemoService()
    
    @app.post("/validate")
    async def validate_endpoint(data: dict[str, Any]) -> dict[str, Any]:
        """Validation endpoint."""
        return service.validate_input(data)
    
    @app.get("/network/{endpoint}")
    async def network_endpoint(endpoint: str) -> dict[str, Any]:
        """Network call endpoint."""
        return service.simulate_network_call(f"https://{endpoint}")
    
    @app.get("/unstable")
    async def unstable_endpoint() -> dict[str, Any]:
        """Unstable service endpoint."""
        return service.simulate_unstable_service()
    
    @app.post("/workflow")
    async def workflow_endpoint(user_id: str, session_id: str) -> dict[str, Any]:
        """Workflow endpoint."""
        return service.complex_workflow(user_id, session_id)
    
    print("FastAPI app created with endpoints:")
    print("- POST /validate - Validation with error handling")
    print("- GET /network/{endpoint} - Network calls with retry")
    print("- GET /unstable - Circuit breaker protection")
    print("- POST /workflow - Complex workflow with context tracking")
    print()
    print("To run the API:")
    print("  uvicorn error_handling_demo:demo_fastapi_integration --reload")
    print()


def main():
    """Run all demonstrations."""
    print("🚀 OmniMind Error Handling System Demo")
    print("=" * 50)
    print()
    
    try:
        # Demo setup utilities
        app, grpc_server = demo_setup_utilities()
        
        # Demo error handling patterns
        demo_error_handling_patterns()
        
        # Demo custom exceptions
        demo_custom_exceptions()
        
        # Demo FastAPI integration
        demo_fastapi_integration()
        
        print("✅ All demos completed successfully!")
        print()
        print("📚 Additional Resources:")
        print("- docs/error_handling_patterns.md - Comprehensive patterns guide")
        print("- examples/service_with_error_handling.py - Complete service example")
        print("- examples/error_handling_integration.py - Integration examples")
        print()
        print("🧪 Testing:")
        print("  pytest tests/unit/utils/test_error_setup.py")
        print()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
