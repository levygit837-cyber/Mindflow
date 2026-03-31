"""Enhanced gRPC usage example with monitoring and resilience.

This script demonstrates the new enhanced gRPC client and server
with comprehensive monitoring, circuit breaker, retry policies,
timeout management, and health checking.
"""

import asyncio
import logging

from mindflow_backend.grpc.client import EnhancedGrpcAgentClient
from mindflow_backend.grpc.config import GrpcClientConfig, GrpcConfig
from mindflow_backend.grpc.monitoring.metrics import GrpcMetricsCollector
from mindflow_backend.grpc.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    GrpcCircuitBreaker,
)
from mindflow_backend.grpc.resilience.retry import AdvancedRetryPolicy, RetryConfig
from mindflow_backend.grpc.resilience.timeout import TimeoutConfig, TimeoutManager
from mindflow_backend.grpc.server import (
    EnhancedGrpcAgentServer,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def example_enhanced_grpc_client():
    """Example of using the enhanced gRPC client with all features."""
    print("🚀 Enhanced gRPC Client Example")
    print("=" * 60)
    
    # Create enhanced client with all features enabled
    print("\n1. Enhanced gRPC Client with Monitoring & Resilience:")
    try:
        client_config = GrpcClientConfig(
            host="localhost",
            port=50051,
            secure=False,
            max_attempts=3,
            connection_timeout_seconds=10,
            request_timeout_seconds=30,
            pool_size=10,
            max_pool_size=50,
        )
        
        client = EnhancedGrpcAgentClient(
            config=client_config,
            enable_monitoring=True,
            enable_circuit_breaker=True,
            enable_retry=True,
            enable_timeout_management=True,
        )
        
        # Use as context manager (recommended)
        async with client:
            print("   ✅ Client connected successfully")
            
            # Get comprehensive statistics
            stats = client.get_statistics()
            print(f"   📊 Client Features: {list(stats['client_info']['features'].keys())}")
            
            # Health check with detailed information
            health = await client.health_check()
            print(f"   🏥 Health Status: {health['status']}")
            
            if 'circuit_breaker' in health:
                print(f"   ⚡ Circuit Breaker: {health['circuit_breaker']['state']} ({health['circuit_breaker']['success_rate']})")
            
            if 'retry' in health:
                print(f"   🔄 Retry Success Rate: {health['retry']['success_rate']}")
            
            # Test streaming with resilience
            if health['status'] == 'healthy':
                print("   🌊 Testing stream chat with resilience...")
                event_count = 0
                start_time = asyncio.get_event_loop().time()
                
                async for event in client.stream_chat(
                    session_id="enhanced-example-session",
                    message="Hello from enhanced gRPC client!",
                    provider="openai",
                    model="gpt-4",
                    debug_steps=True,
                ):
                    print(f"   Event {event.seq}: {event.type} - {event.data[:50]}...")
                    event_count += 1
                    if event_count >= 5:  # Limit for demo
                        break
                
                duration = asyncio.get_event_loop().time() - start_time
                print(f"   ⏱️  Stream completed in {duration:.2f}s with {event_count} events")
                
                # Show final statistics
                final_stats = client.get_statistics()
                if 'metrics' in final_stats:
                    metrics = final_stats['metrics']
                    print(f"   📈 Connection Metrics: {metrics['total_active_connections']} active, {metrics['total_connection_errors']} errors")
                
                if 'circuit_breaker' in final_stats:
                    cb_stats = final_stats['circuit_breaker']
                    print(f"   ⚡ Circuit Breaker: {cb_stats['total_calls']} calls, {cb_stats['success_rate_percent']:.1f}% success")
                
                if 'retry' in final_stats:
                    retry_stats = final_stats['retry']
                    print(f"   🔄 Retry Stats: {retry_stats['total_attempts']} attempts, {retry_stats['success_rate']:.1f}% success")
                
                if 'timeout' in final_stats:
                    timeout_stats = final_stats['timeout']
                    print(f"   ⏱️  Timeout Stats: {timeout_stats['total_operations']} operations, {timeout_stats['timeout_rate']:.1f}% timeout rate")
            else:
                print("   ⚠️  Server not healthy, skipping stream chat demo")
                
    except Exception as exc:
        print(f"   ❌ Error: {exc}")
        print("   Note: This is expected if gRPC server is not running")


async def example_enhanced_grpc_server():
    """Example of using the enhanced gRPC server with monitoring."""
    print("\n🔧 Enhanced gRPC Server Example")
    print("=" * 60)
    
    try:
        # Create enhanced server configuration
        config = GrpcConfig(
            enabled=True,
            auto_start=True,
            host="localhost",
            port=50051,
            secure=False,
            enable_metrics=True,
            enable_health_check=True,
            grpc_prometheus_port=9090,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=5,
            timeout_adaptive=True,
        )
        
        server = EnhancedGrpcAgentServer(config)
        
        print(f"   🚀 Starting enhanced server on {server.get_host()}:{server.get_port()}...")
        
        # Start server
        await server.start()
        
        print("   ✅ Enhanced server started successfully!")
        print(f"   📊 Features enabled: {list(server.get_server_info()['features'].keys())}")
        
        # Get server information
        server_info = server.get_server_info()
        print(f"   🖥️  Server Config: {server_info['config']['enable_metrics']} metrics, {server_info['config']['enable_health_check']} health check")
        
        # Get health report
        health_report = await server.get_health_report()
        print(f"   🏥 Health Status: {health_report['status']}")
        
        if 'checks' in health_report:
            print(f"   🔍 Health Checks: {len(health_report['checks'])} checks performed")
            for check in health_report['checks']:
                print(f"      - {check['name']}: {check['status']} ({check['duration_ms']:.1f}ms)")
        
        # Get metrics summary
        metrics_summary = server.get_metrics_summary()
        if 'request_metrics' in metrics_summary:
            print(f"   📈 Request Metrics: {len(metrics_summary['request_metrics'])} methods tracked")
        
        # Show Prometheus endpoint if enabled
        if server.prometheus_exporter:
            print(f"   📊 Prometheus Metrics: {server.prometheus_exporter.get_metrics_url()}")
        
        # Keep server running for a bit
        print("   ⏳ Server will run for 15 seconds...")
        await asyncio.sleep(15)
        
        # Show final statistics
        final_metrics = server.get_metrics_summary()
        if 'business_metrics' in final_metrics:
            business = final_metrics['business_metrics']
            print(f"   💼 Business Metrics: {business['chat_requests_per_second']:.2f} RPS, {business['average_session_duration_seconds']:.1f}s avg session")
        
        # Stop server
        await server.stop()
        print("   ✅ Enhanced server stopped gracefully")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")
        print("   Note: This might fail if gRPC bindings are not generated")


async def example_circuit_breaker():
    """Example of circuit breaker functionality."""
    print("\n⚡ Circuit Breaker Example")
    print("=" * 60)
    
    # Create circuit breaker configuration
    circuit_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=10.0,
        success_threshold=2,
        timeout=5.0,
    )
    
    circuit_breaker = GrpcCircuitBreaker("example-service", circuit_config)
    
    print("   🔧 Circuit Breaker Configuration:")
    print(f"      - Failure Threshold: {circuit_config.failure_threshold}")
    print(f"      - Recovery Timeout: {circuit_config.recovery_timeout}s")
    print(f"      - Success Threshold: {circuit_config.success_threshold}")
    
    # Simulate operations
    async def failing_operation():
        await asyncio.sleep(0.1)
        raise ConnectionError("Simulated connection failure")
    
    async def successful_operation():
        await asyncio.sleep(0.1)
        return "Success!"
    
    print("\n   🧪 Testing Circuit Breaker:")
    
    # Test successful operation
    try:
        result = await circuit_breaker.call(successful_operation)
        print(f"   ✅ Successful operation: {result}")
    except Exception as exc:
        print(f"   ❌ Operation failed: {exc}")
    
    # Test failing operations to trigger circuit breaker
    print("\n   💥 Triggering failures to open circuit...")
    for i in range(4):  # Exceed threshold
        try:
            result = await circuit_breaker.call(failing_operation)
            print(f"   ✅ Operation {i+1}: {result}")
        except Exception as exc:
            print(f"   ❌ Operation {i+1} failed: {type(exc).__name__}")
    
    # Show circuit breaker state
    stats = circuit_breaker.get_statistics()
    print(f"\n   📊 Circuit Breaker State: {stats['state']}")
    print(f"      - Failure Count: {stats['failure_count']}")
    print(f"      - Success Rate: {stats['success_rate_percent']:.1f}%")
    
    # Test operation when circuit is open
    print("\n   🚫 Testing operation when circuit is OPEN:")
    try:
        result = await circuit_breaker.call(successful_operation)
        print(f"   ✅ Operation succeeded: {result}")
    except Exception as exc:
        print(f"   ❌ Operation failed (expected): {type(exc).__name__}")
    
    print(f"\n   ⏱️  Waiting for recovery timeout ({circuit_config.recovery_timeout}s)...")
    await asyncio.sleep(circuit_config.recovery_timeout + 1)
    
    # Test operation after recovery timeout
    print("\n   🔄 Testing operation after recovery timeout:")
    try:
        result = await circuit_breaker.call(successful_operation)
        print(f"   ✅ Operation succeeded: {result}")
    except Exception as exc:
        print(f"   ❌ Operation failed: {type(exc).__name__}")
    
    # Show final statistics
    final_stats = circuit_breaker.get_statistics()
    print("\n   📊 Final Statistics:")
    print(f"      - Total Calls: {final_stats['total_calls']}")
    print(f"      - Success Rate: {final_stats['success_rate_percent']:.1f}%")
    print(f"      - Final State: {final_stats['state']}")


async def example_retry_policies():
    """Example of advanced retry policies."""
    print("\n🔄 Advanced Retry Policies Example")
    print("=" * 60)
    
    # Create retry configuration
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=0.1,
        max_delay=2.0,
        multiplier=2.0,
        jitter=True,
    )
    
    retry_policy = AdvancedRetryPolicy(retry_config)
    
    print("   🔧 Retry Policy Configuration:")
    print(f"      - Max Attempts: {retry_config.max_attempts}")
    print(f"      - Base Delay: {retry_config.base_delay}s")
    print(f"      - Max Delay: {retry_config.max_delay}s")
    print(f"      - Multiplier: {retry_config.multiplier}x")
    print(f"      - Jitter: {retry_config.jitter}")
    
    # Test operations
    attempt_count = 0
    
    async def sometimes_failing_operation():
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count < 2:
            raise ConnectionError(f"Attempt {attempt_count} failed")
        
        return f"Success on attempt {attempt_count}!"
    
    print("\n   🧪 Testing Retry Policy:")
    
    try:
        start_time = asyncio.get_event_loop().time()
        result = await retry_policy.execute_with_retry(sometimes_failing_operation)
        duration = asyncio.get_event_loop().time() - start_time
        
        print(f"   ✅ Operation succeeded: {result}")
        print(f"   ⏱️  Total duration: {duration:.2f}s")
        
    except Exception as exc:
        print(f"   ❌ Operation failed: {type(exc).__name__}")
    
    # Show retry statistics
    stats = retry_policy.get_statistics()
    print("\n   📊 Retry Statistics:")
    print(f"      - Total Attempts: {stats['total_attempts']}")
    print(f"      - Success Rate: {stats['success_rate']:.1f}%")
    print(f"      - Average Duration: {stats['average_duration']:.3f}s")
    
    if stats['error_distribution']:
        print(f"      - Error Distribution: {stats['error_distribution']}")


async def example_timeout_management():
    """Example of timeout management."""
    print("\n⏱️  Timeout Management Example")
    print("=" * 60)
    
    # Create timeout configuration
    timeout_config = TimeoutConfig(
        default_timeout=2.0,
        short_timeout=0.5,
        long_timeout=5.0,
        streaming_timeout=10.0,
        enable_adaptive=True,
        enable_deadline_propagation=True,
    )
    
    timeout_manager = TimeoutManager(timeout_config)
    
    print("   🔧 Timeout Configuration:")
    print(f"      - Default Timeout: {timeout_config.default_timeout}s")
    print(f"      - Short Timeout: {timeout_config.short_timeout}s")
    print(f"      - Long Timeout: {timeout_config.long_timeout}s")
    print(f"      - Adaptive: {timeout_config.enable_adaptive}")
    
    # Test operations
    async def fast_operation():
        await asyncio.sleep(0.1)
        return "Fast operation completed"
    
    async def slow_operation():
        await asyncio.sleep(3.0)
        return "Slow operation completed"
    
    print("\n   🧪 Testing Timeout Management:")
    
    # Test fast operation
    try:
        async with timeout_manager.timeout_context("fast_operation"):
            result = await fast_operation()
            print(f"   ✅ Fast operation: {result}")
    except Exception as exc:
        print(f"   ❌ Fast operation failed: {type(exc).__name__}")
    
    # Test slow operation (should timeout)
    try:
        async with timeout_manager.timeout_context("slow_operation"):
            result = await slow_operation()
            print(f"   ✅ Slow operation: {result}")
    except Exception as exc:
        print(f"   ❌ Slow operation timed out (expected): {type(exc).__name__}")
    
    # Show timeout statistics
    stats = timeout_manager.get_statistics()
    print("\n   📊 Timeout Statistics:")
    print(f"      - Total Operations: {stats['total_operations']}")
    print(f"      - Successful Operations: {stats['successful_operations']}")
    print(f"      - Timeout Operations: {stats['timeout_operations']}")
    print(f"      - Timeout Rate: {stats['timeout_rate']:.1f}%")
    print(f"      - Average Duration: {stats['average_duration']:.3f}s")


async def example_monitoring_dashboard():
    """Example of monitoring and dashboard features."""
    print("\n📊 Monitoring Dashboard Example")
    print("=" * 60)
    
    # Create metrics collector
    metrics_collector = GrpcMetricsCollector()
    
    # Simulate some activity
    print("   📈 Simulating gRPC activity...")
    
    for i in range(10):
        # Record requests
        start_time = metrics_collector.record_request_start("StreamChat", f"req-{i}")
        await asyncio.sleep(0.01)  # Simulate processing
        metrics_collector.record_request_complete("StreamChat", f"req-{i}", start_time, "OK")
        
        # Record chat requests
        metrics_collector.record_chat_request()
        
        # Record session duration
        metrics_collector.record_session_duration(30.0 + i * 5)
        
        # Record agent performance
        metrics_collector.record_agent_performance("chat_agent", 1.5 + i * 0.1, True)
    
    # Get comprehensive metrics
    print("\n   📊 Metrics Summary:")
    
    # Request metrics
    request_metrics = metrics_collector.get_request_metrics()
    if request_metrics:
        for method, metrics in request_metrics.items():
            print(f"      - {method}: {metrics['request_count']} requests, {metrics['success_rate']:.1%} success, {metrics['average_duration']:.3f}s avg")
    
    # Connection metrics
    connection_metrics = metrics_collector.get_connection_metrics()
    print(f"      - Connections: {connection_metrics['total_active_connections']} active, {connection_metrics['total_connection_errors']} errors")
    
    # Business metrics
    business_metrics = metrics_collector.get_business_metrics()
    print(f"      - Business: {business_metrics['chat_requests_per_second']:.2f} RPS, {business_metrics['average_session_duration_seconds']:.1f}s avg session")
    
    # Latency summary
    latency_summary = metrics_collector.get_latency_summary()
    if latency_summary:
        print(f"      - Latency: P50={latency_summary['percentiles']['p50']:.3f}s, P95={latency_summary['percentiles']['p95']:.3f}s, P99={latency_summary['percentiles']['p99']:.3f}s")
    
    # System metrics
    system_metrics = metrics_collector.get_system_metrics()
    print(f"      - System: {system_metrics['cpu_usage_percent']:.1f}% CPU, {system_metrics['memory_usage_mb']:.1f}MB memory")


async def main():
    """Run all enhanced examples."""
    print("🎯 MindFlow Enhanced gRPC Implementation Examples")
    print("=" * 70)
    print("This script demonstrates the enhanced gRPC client and server")
    print("with comprehensive monitoring, resilience, and advanced features.")
    print()
    
    # Run examples
    await example_enhanced_grpc_client()
    await example_enhanced_grpc_server()
    await example_circuit_breaker()
    await example_retry_policies()
    await example_timeout_management()
    await example_monitoring_dashboard()
    
    print("\n✅ Enhanced Examples Completed!")
    print("\n🚀 Next Steps:")
    print("1. Generate gRPC bindings: bash scripts/gen_proto.sh")
    print("2. Start the application: python -m mindflow_backend.main")
    print("3. View Prometheus metrics: http://localhost:9090/metrics")
    print("4. Check health status: http://localhost:8000/health")
    print("5. Monitor circuit breakers and retry policies in logs")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run examples
    asyncio.run(main())
