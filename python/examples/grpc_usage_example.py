"""Example usage of the new gRPC implementation.

This script demonstrates how to use the enhanced gRPC client and server
with proper connection management, error handling, and monitoring.
"""

import asyncio
import logging

from mindflow_backend.grpc.client import GrpcAgentClient, LocalAgentClient
from mindflow_backend.grpc.config import GrpcClientConfig, GrpcConfig
from mindflow_backend.grpc.server import GrpcAgentServer, start_grpc_server, stop_grpc_server
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def example_grpc_client_usage():
    """Example of using the gRPC client."""
    print("🚀 gRPC Client Example")
    print("=" * 50)
    
    # Option 1: Use real gRPC client
    print("\n1. Real gRPC Client:")
    try:
        client = GrpcAgentClient(
            host="localhost",
            port=50051,
            secure=False,
            max_attempts=3,
            timeout_seconds=30,
        )
        
        # Use as context manager (recommended)
        async with client:
            # Health check
            health = await client.health_check()
            print(f"   Server health: {health}")
            
            # Stream chat (if server is running)
            if health["status"] == "healthy":
                print("   Streaming chat response...")
                event_count = 0
                async for event in client.stream_chat(
                    session_id="example-session",
                    message="Hello, gRPC world!",
                    provider="openai",
                    model="gpt-4",
                    debug_steps=True,
                ):
                    print(f"   Event {event.seq}: {event.type} - {event.data[:50]}...")
                    event_count += 1
                    if event_count >= 5:  # Limit for demo
                        break
            else:
                print("   Server not available, skipping stream chat demo")
                
    except Exception as exc:
        print(f"   Error: {exc}")
        print("   Note: This is expected if gRPC server is not running")
    
    # Option 2: Use fallback local client (for development)
    print("\n2. Local Fallback Client:")
    try:
        local_client = LocalAgentClient()
        
        print("   Streaming with local client...")
        event_count = 0
        async for event in local_client.stream_chat(
            session_id="local-example-session",
            message="Hello, local world!",
            provider="openai",
            model="gpt-4",
        ):
            print(f"   Event {event.seq}: {event.type} - {event.data[:50]}...")
            event_count += 1
            if event_count >= 5:  # Limit for demo
                break
                
    except Exception as exc:
        print(f"   Error: {exc}")


async def example_grpc_server_usage():
    """Example of using the gRPC server."""
    print("\n🔧 gRPC Server Example")
    print("=" * 50)
    
    try:
        # Create server instance
        server = GrpcAgentServer()
        
        print(f"   Starting server on {server.get_host()}:{server.get_port()}...")
        
        # Start server
        await server.start()
        
        print("   ✅ Server started successfully!")
        print(f"   Status: {'Running' if server.is_running() else 'Stopped'}")
        print(f"   Uptime: {server.get_uptime_seconds():.2f} seconds")
        
        # Keep server running for a bit
        print("   Server will run for 10 seconds...")
        await asyncio.sleep(10)
        
        # Stop server
        await server.stop()
        print("   ✅ Server stopped gracefully")
        
    except Exception as exc:
        print(f"   Error: {exc}")
        print("   Note: This might fail if gRPC bindings are not generated")


async def example_configuration_usage():
    """Example of using gRPC configuration."""
    print("\n⚙️  Configuration Example")
    print("=" * 50)
    
    # Server configuration
    server_config = GrpcConfig(
        enabled=True,
        auto_start=True,
        host="localhost",
        port=50051,
        secure=False,
        max_connections=100,
        connection_timeout_seconds=30,
        max_attempts=3,
        default_timeout_seconds=300,
        enable_metrics=True,
        enable_health_check=True,
        debug_mode=True,
    )
    
    print("   Server Configuration:")
    print(f"   - Enabled: {server_config.enabled}")
    print(f"   - Auto Start: {server_config.auto_start}")
    print(f"   - Host: {server_config.host}")
    print(f"   - Port: {server_config.port}")
    print(f"   - Secure: {server_config.secure}")
    print(f"   - Max Connections: {server_config.max_connections}")
    print(f"   - Timeout: {server_config.connection_timeout_seconds}s")
    print(f"   - Max Attempts: {server_config.max_attempts}")
    print(f"   - Metrics: {server_config.enable_metrics}")
    print(f"   - Health Check: {server_config.enable_health_check}")
    
    # Client configuration from server config
    client_config = GrpcClientConfig.from_server_config(server_config)
    
    print("\n   Client Configuration (from server):")
    print(f"   - Host: {client_config.host}")
    print(f"   - Port: {client_config.port}")
    print(f"   - Secure: {client_config.secure}")
    print(f"   - Pool Size: {client_config.pool_size}")
    print(f"   - Max Attempts: {client_config.max_attempts}")
    print(f"   - Connection Timeout: {client_config.connection_timeout_seconds}s")
    print(f"   - Request Timeout: {client_config.request_timeout_seconds}s")


async def example_integrated_usage():
    """Example of integrated client-server usage."""
    print("\n🔄 Integrated Usage Example")
    print("=" * 50)
    
    try:
        # Start server
        print("   Starting gRPC server...")
        server = await start_grpc_server()
        print(f"   ✅ Server running on {server.get_host()}:{server.get_port()}")
        
        # Create client
        print("   Creating gRPC client...")
        client = GrpcAgentClient(
            host=server.get_host(),
            port=server.get_port(),
            max_attempts=3,
            timeout_seconds=10,
        )
        
        # Connect and test
        async with client:
            print("   Testing health check...")
            health = await client.health_check()
            print(f"   Health: {health}")
            
            if health["status"] == "healthy":
                print("   Testing stream chat...")
                event_count = 0
                async for event in client.stream_chat(
                    session_id="integrated-session",
                    message="Hello from integrated example!",
                    provider="openai",
                    model="gpt-4",
                ):
                    print(f"   Event {event.seq}: {event.type}")
                    event_count += 1
                    if event_count >= 3:
                        break
        
        # Stop server
        await stop_grpc_server()
        print("   ✅ Server stopped")
        
    except Exception as exc:
        print(f"   Error: {exc}")
        print("   Note: This requires generated gRPC bindings")


async def example_error_handling():
    """Example of error handling in gRPC operations."""
    print("\n🛡️  Error Handling Example")
    print("=" * 50)
    
    # Connection error handling
    print("   1. Connection Error Handling:")
    try:
        client = GrpcAgentClient(
            host="nonexistent-host",
            port=99999,
            max_attempts=2,
            timeout_seconds=1,
        )
        
        await client.connect()
        
    except ConnectionError as exc:
        print(f"   ✅ Caught connection error: {exc}")
    except Exception as exc:
        print(f"   ❌ Unexpected error: {exc}")
    
    # Timeout error handling
    print("\n   2. Timeout Error Handling:")
    try:
        client = GrpcAgentClient(
            host="localhost",
            port=50051,
            timeout_seconds=0.001,  # Very short timeout
        )
        
        async with client:
            # This might timeout if server takes too long
            health = await client.health_check()
            print(f"   Health check completed: {health['status']}")
            
    except TimeoutError as exc:
        print(f"   ✅ Caught timeout error: {exc}")
    except Exception as exc:
        print(f"   Note: {exc}")


async def main():
    """Run all examples."""
    print("🎯 MindFlow gRPC Implementation Examples")
    print("=" * 60)
    print("This script demonstrates the new gRPC client and server")
    print("implementation with proper error handling and monitoring.")
    print()
    
    # Run examples
    await example_configuration_usage()
    await example_grpc_client_usage()
    await example_grpc_server_usage()
    await example_integrated_usage()
    await example_error_handling()
    
    print("\n✅ Examples completed!")
    print("\nNext steps:")
    print("1. Generate gRPC bindings: bash scripts/gen_proto.sh")
    print("2. Start the application: python -m mindflow_backend.main")
    print("3. Test gRPC endpoints with a gRPC client")
    print("4. Monitor gRPC server health via /health endpoint")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run examples
    asyncio.run(main())
