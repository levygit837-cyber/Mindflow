#!/usr/bin/env python3
"""Simplified exception handling demo following best practices.

This demonstrates the new simplified exception system that follows
the patterns observed in examples - simple, direct, and practical.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindflow_backend.exceptions import (
    MindFlowError, AgentSystemError, ContextRetrievalError,
    NetworkError, TimeoutError, ErrorFactory, AgentErrors,
    AgentCommunicationError, InfrastructureError
)
from mindflow_backend.exceptions.base.core_simple import NetworkError as BaseNetworkError, TimeoutError as BaseTimeoutError, InfrastructureError as BaseInfrastructureError


def demo_simple_exceptions():
    """Demonstrate simple exception creation following examples pattern."""
    print("🚀 Simple Exception Handling Demo")
    print("=" * 50)
    
    # 1. Basic exception - simple and direct
    print("\n1. Basic exception (like examples):")
    try:
        raise MindFlowError("Processing failed", component="DemoService")
    except MindFlowError as e:
        print(f"   ✅ Error ID: {e.error_id}")
        print(f"   ✅ Component: {e.component}")
        print(f"   ✅ Message: {e}")
    
    # 2. Context-rich exception - still simple
    print("\n2. Context-rich exception:")
    try:
        raise AgentSystemError(
            "Agent execution failed",
            agent_type="SpecialistAgent",
            task_id="task_123"
        )
    except AgentSystemError as e:
        print(f"   ✅ Agent type: {e.agent_type}")
        print(f"   ✅ Task ID: {e.task_id}")
        print(f"   ✅ Component: {e.component}")
    
    # 3. Factory methods - following examples pattern
    print("\n3. Factory methods (examples pattern):")
    try:
        network_error = ErrorFactory.network_failure("https://api.example.com")
        raise network_error
    except BaseNetworkError as e:
        print(f"   ✅ Endpoint: {e.endpoint}")
        print(f"   ✅ Service: {e.service}")
    
    # 4. Agent factory methods
    print("\n4. Agent factory methods:")
    try:
        exec_error = AgentErrors.execution_failed('DataProcessor', 'task_123', 'Invalid input')
        raise exec_error
    except AgentSystemError as e:
        print(f"   ✅ Agent type: {e.agent_type}")
        print(f"   ✅ Task ID: {e.task_id}")
    
    # 5. More factory methods
    print("\n5. Extended factory methods:")
    try:
        comm_error = AgentErrors.communication_failed('Agent1', 'Agent2', 'Connection refused')
        raise comm_error
    except AgentCommunicationError as e:
        print(f"   ✅ Source: {e.source_agent}")
        print(f"   ✅ Target: {e.target_agent}")
    
    # 6. Infrastructure factory methods
    print("\n6. Infrastructure factory methods:")
    try:
        infra_error = ErrorFactory.infrastructure_failure('database', 'connect', 'Connection timeout')
        raise infra_error
    except BaseInfrastructureError as e:
        print(f"   ✅ Service: {e.service}")
    
    # 7. Optional fluent interface - not required
    print("\n7. Optional fluent interface:")
    try:
        complex_error = (MindFlowError("Complex error")
         .with_context(operation="demo", step="validation")
         .caused_by(ValueError("Invalid input")))
        raise complex_error
    except MindFlowError as e:
        print(f"   ✅ Context: {e.context}")
        print(f"   ✅ Cause: {e.cause}")


def demo_error_handling_patterns():
    """Demonstrate error handling patterns like in examples."""
    print("\n\n🔄 Error Handling Patterns (like examples)")
    print("=" * 50)
    
    # Simulate operations that can fail
    def simulate_network_call(endpoint: str, should_fail: bool = False):
        if should_fail:
            raise ErrorFactory.network_failure(endpoint)
        return f"Data from {endpoint}"
    
    def simulate_agent_execution(agent_type: str, should_fail: bool = False):
        if should_fail:
            raise AgentErrors.execution_timeout(agent_type, 30.0)
        return f"Result from {agent_type}"
    
    # Test with specific error handling (examples pattern)
    print("\n1. Specific error handling:")
    try:
        result = simulate_network_call("https://api.test.com", should_fail=True)
    except BaseNetworkError as e:
        print(f"   ✅ Caught network error: {e}")
        print(f"   ✅ Endpoint: {e.endpoint}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    
    print("\n2. Timeout error handling:")
    try:
        result = simulate_agent_execution("DataProcessor", should_fail=True)
    except BaseTimeoutError as e:
        print(f"   ✅ Caught timeout: {e}")
        print(f"   ✅ Timeout seconds: {e.timeout_seconds}")
    except AgentSystemError as e:
        print(f"   ✅ Caught agent error: {e}")
    
    print("\n3. Multiple error types:")
    try:
        # Simulate different failure scenarios
        import random
        failure_type = random.choice(["network", "timeout", "context"])
        
        if failure_type == "network":
            raise ErrorFactory.network_failure("https://service.com")
        elif failure_type == "timeout":
            raise ErrorFactory.timeout("data_processing", 60.0)
        else:
            raise AgentErrors.context_failed("session_123")
            
    except BaseNetworkError as e:
        print(f"   ✅ Network failure: {e.endpoint}")
    except BaseTimeoutError as e:
        print(f"   ✅ Operation timeout: {e.timeout_seconds}s")
    except ContextRetrievalError as e:
        print(f"   ✅ Context retrieval failed: {e.session_id}")


def demo_backward_compatibility():
    """Demonstrate backward compatibility."""
    print("\n\n🔄 Backward Compatibility Demo")
    print("=" * 50)
    
    # Old patterns still work
    print("\n1. Old-style exception creation still works:")
    try:
        raise MindFlowError("Old style error")
    except MindFlowError as e:
        print(f"   ✅ Basic exception: {e}")
    
    print("\n2. Context can be added later:")
    error = MindFlowError("Initial error")
    error.with_context(operation="demo", step="compatibility")
    print(f"   ✅ Added context: {error.context}")


if __name__ == "__main__":
    try:
        demo_simple_exceptions()
        demo_error_handling_patterns()
        demo_backward_compatibility()
        
        print("\n\n✅ All demos completed successfully!")
        print("\n📚 Key improvements:")
        print("- Simpler inheritance hierarchy")
        print("- Factory methods for common cases")
        print("- Optional fluent interface")
        print("- Better naming conventions")
        print("- Backward compatibility maintained")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
