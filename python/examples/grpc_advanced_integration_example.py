#!/usr/bin/env python3
"""
gRPC Advanced Features Integration Example

Demonstrates the complete integration of dynamic configuration,
environment profiles, feature flags, enhanced monitoring, and resilience
patterns in the OmniMind gRPC system.
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindflow_backend.grpc.config import GrpcConfig, GrpcClientConfig
from mindflow_backend.grpc.config.dynamic.manager import get_config_manager
from mindflow_backend.grpc.config.profiles import get_environment_loader
from mindflow_backend.grpc.server import EnhancedGrpcAgentServer
from mindflow_backend.grpc.client import EnhancedGrpcAgentClient
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class GrpcAdvancedIntegrationExample:
    """Example demonstrating gRPC advanced features integration."""
    
    def __init__(self):
        self.config_manager = None
        self.grpc_config = None
        self.server = None
        self.client = None
        
    async def setup_dynamic_configuration(self):
        """Setup dynamic configuration system."""
        print("🔧 Setting up Dynamic Configuration...")
        
        # Initialize config manager
        self.config_manager = get_config_manager()
        await self.config_manager.initialize()
        
        # Load dynamic configuration with environment detection
        self.grpc_config = await GrpcConfig.load_dynamic()
        
        print(f"   ✅ Config loaded: {self.grpc_config.host}:{self.grpc_config.port}")
        print(f"   ✅ Profile: {self.grpc_config.profile}")
        print(f"   ✅ Features: monitoring={self.grpc_config.enable_metrics}")
        print(f"   ✅ Resilience: circuit_breaker={self.grpc_config.circuit_breaker_enabled}")
        
    async def demonstrate_environment_profiles(self):
        """Demonstrate environment profile switching."""
        print("\n🌍 Demonstrating Environment Profiles...")
        
        env_loader = get_environment_loader()
        
        # List available profiles
        profiles = env_loader.list_profiles()
        print(f"   Available profiles: {[p['name'] for p in profiles]}")
        
        # Apply different profiles
        for profile_name in ['development', 'staging', 'production']:
            print(f"\n   Applying {profile_name} profile:")
            profile_config = await env_loader.load_profile_config(profile_name, self.grpc_config)
            
            print(f"   - Debug mode: {profile_config.debug_mode}")
            print(f"   - Max connections: {profile_config.max_connections}")
            print(f"   - Circuit breaker threshold: {profile_config.circuit_breaker_threshold}")
            print(f"   - Monitoring enabled: {profile_config.enable_metrics}")
    
    async def demonstrate_dynamic_updates(self):
        """Demonstrate dynamic configuration updates."""
        print("\n⚡ Demonstrating Dynamic Updates...")
        
        # Test various configuration updates
        updates = [
            {
                'description': 'Enable debug mode',
                'changes': {'debug_mode': True, 'reflection_enabled': True}
            },
            {
                'description': 'Increase performance settings',
                'changes': {
                    'max_connections': 500,
                    'connection_timeout_seconds': 15,
                    'default_timeout_seconds': 120
                }
            },
            {
                'description': 'Enable advanced monitoring',
                'changes': {
                    'enable_metrics': True,
                    'metrics_history_size': 2000,
                    'system_metrics_interval': 2
                }
            },
            {
                'description': 'Configure circuit breaker',
                'changes': {
                    'circuit_breaker_enabled': True,
                    'circuit_breaker_threshold': 10,
                    'circuit_breaker_recovery_timeout': 30
                }
            }
        ]
        
        for i, update in enumerate(updates, 1):
            print(f"\n   Update {i}: {update['description']}")
            success = await self.config_manager.update_config(
                update['changes'], 
                update['description']
            )
            print(f"   ✅ Success: {success}")
            
            # Get updated config
            updated_config = await self.config_manager.get_current_config()
            print(f"   📊 Current version: {getattr(updated_config, 'version', 'unknown')}")
    
    async def setup_enhanced_server(self):
        """Setup enhanced gRPC server with all features."""
        print("\n🚀 Setting up Enhanced gRPC Server...")
        
        # Create enhanced server with dynamic configuration
        self.server = EnhancedGrpcAgentServer(self.grpc_config)
        
        print(f"   ✅ Server created with host: {self.server.config.host}")
        print(f"   ✅ Port: {self.server.config.port}")
        print(f"   ✅ Security: {self.server.config.secure}")
        print(f"   ✅ Features enabled: {len([f for f in ['monitoring', 'health_check', 'circuit_breaker', 'retry'] if getattr(self.server.config, f.replace('_', '_enabled'), False)])}")
        
        # Start server
        await self.server.start()
        print(f"   ✅ Server started successfully")
        
        # Get server information
        server_info = self.server.get_server_info()
        print(f"   ✅ Server uptime: {server_info['server']['uptime_seconds']:.2f}s")
        print(f"   ✅ Available features: {list(server_info['features'].keys())}")
    
    async def setup_enhanced_client(self):
        """Setup enhanced gRPC client with all features."""
        print("\n🔌 Setting up Enhanced gRPC Client...")
        
        # Create client configuration from server config
        client_config = GrpcClientConfig.from_server_config(self.grpc_config)
        
        # Create enhanced client with all features enabled
        self.client = EnhancedGrpcAgentClient(
            config=client_config,
            enable_monitoring=True,
            enable_circuit_breaker=True,
            enable_retry=True,
            enable_timeout_management=True,
            enable_connection_pooling=True
        )
        
        print(f"   ✅ Client created for {client_config.host}:{client_config.port}")
        print(f"   ✅ Connection pool size: {client_config.pool_size}")
        print(f"   ✅ Load balancing: {client_config.load_balancing_policy}")
        print(f"   ✅ Compression: {client_config.compression_algorithm}")
        print(f"   ✅ Enhanced features: monitoring, circuit_breaker, retry, timeout, pooling")
    
    async def demonstrate_monitoring(self):
        """Demonstrate monitoring and metrics collection."""
        print("\n📊 Demonstrating Monitoring & Metrics...")
        
        if self.server and hasattr(self.server, 'get_metrics_summary'):
            metrics = self.server.get_metrics_summary()
            print("   Server Metrics:")
            print(f"   - Request metrics: {len(metrics.get('request_metrics', {}))} types")
            print(f"   - Connection metrics: {len(metrics.get('connection_metrics', {}))} types")
            print(f"   - System metrics: {len(metrics.get('system_metrics', {}))} types")
            print(f"   - Latency summary: {metrics.get('latency_summary', {})}")
        
        if self.client and hasattr(self.client, 'get_statistics'):
            stats = self.client.get_statistics()
            print("   Client Statistics:")
            print(f"   - Active connections: {stats.get('active_connections', 0)}")
            print(f"   - Total requests: {stats.get('total_requests', 0)}")
            print(f"   - Success rate: {stats.get('success_rate', 0):.2%}")
            print(f"   - Circuit breaker state: {stats.get('circuit_breaker_state', 'CLOSED')}")
    
    async def demonstrate_resilience(self):
        """Demonstrate resilience patterns."""
        print("\n🛡️ Demonstrating Resilience Patterns...")
        
        if self.client:
            # Test circuit breaker behavior
            print("   Testing circuit breaker...")
            try:
                # This would normally make a gRPC call
                # For demonstration, we'll just check the circuit breaker state
                if hasattr(self.client, 'circuit_breaker'):
                    print(f"   - Circuit breaker state: {self.client.circuit_breaker.state}")
                    print(f"   - Failure threshold: {self.client.circuit_breaker.failure_threshold}")
                    print(f"   - Recovery timeout: {self.client.circuit_breaker.recovery_timeout}")
                
                # Test retry policy
                if hasattr(self.client, 'retry_policy'):
                    print(f"   - Max attempts: {self.client.retry_policy.max_attempts}")
                    print(f"   - Backoff multiplier: {self.client.retry_policy.backoff_multiplier}")
                    print(f"   - Jitter enabled: {self.client.retry_policy.jitter_enabled}")
                
                # Test timeout management
                if hasattr(self.client, 'timeout_manager'):
                    print(f"   - Default timeout: {self.client.timeout_manager.default_timeout}")
                    print(f"   - Adaptive timeout: {self.client.timeout_manager.adaptive_enabled}")
                    
            except Exception as e:
                print(f"   - Resilience test error: {e}")
    
    async def demonstrate_configuration_api(self):
        """Demonstrate configuration management API."""
        print("\n🔧 Demonstrating Configuration API...")
        
        if self.config_manager:
            # Get configuration history
            history = await self.config_manager.get_config_history(limit=5)
            print(f"   Configuration history: {len(history)} entries")
            
            for i, entry in enumerate(history, 1):
                print(f"   {i}. {entry['change_type']} - {entry['description']}")
                print(f"      Version: {entry['version']}")
                print(f"      Changed fields: {entry['changed_fields']}")
            
            # Get statistics
            stats = await self.config_manager.get_statistics()
            print(f"   Current statistics:")
            print(f"   - Current version: {stats.get('current_version', 'unknown')}")
            print(f"   - Total updates: {stats.get('total_updates', 0)}")
            print(f"   - Last update: {stats.get('last_update_timestamp', 0)}")
    
    async def cleanup(self):
        """Cleanup resources."""
        print("\n🧹 Cleaning up resources...")
        
        if self.client:
            try:
                await self.client.close()
                print("   ✅ Client closed")
            except Exception as e:
                print(f"   ⚠️ Client close error: {e}")
        
        if self.server and self.server.is_running():
            try:
                await self.server.stop()
                print("   ✅ Server stopped")
            except Exception as e:
                print(f"   ⚠️ Server stop error: {e}")
    
    async def run_demonstration(self):
        """Run the complete demonstration."""
        print("🚀 gRPC Advanced Features Integration Example")
        print("=" * 60)
        
        try:
            # Setup phase
            await self.setup_dynamic_configuration()
            await self.demonstrate_environment_profiles()
            await self.demonstrate_dynamic_updates()
            
            # Server and client setup
            await self.setup_enhanced_server()
            await self.setup_enhanced_client()
            
            # Feature demonstrations
            await self.demonstrate_monitoring()
            await self.demonstrate_resilience()
            await self.demonstrate_configuration_api()
            
            print("\n🎉 gRPC Advanced Features Integration Completed Successfully!")
            print("\n📋 Summary of Implemented Features:")
            print("   ✅ Dynamic Configuration with hot reload")
            print("   ✅ Environment Profiles (dev/staging/prod/local)")
            print("   ✅ Configuration Updates without restart")
            print("   ✅ Enhanced gRPC Server with monitoring")
            print("   ✅ Enhanced gRPC Client with resilience")
            print("   ✅ Circuit Breaker protection")
            print("   ✅ Advanced Retry policies")
            print("   ✅ Timeout management")
            print("   ✅ Connection pooling")
            print("   ✅ Load balancing")
            print("   ✅ Message compression")
            print("   ✅ Real-time metrics collection")
            print("   ✅ Configuration history tracking")
            print("   ✅ Health checks integration")
            
        except Exception as e:
            print(f"\n❌ Demonstration failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.cleanup()


async def main():
    """Main demonstration function."""
    example = GrpcAdvancedIntegrationExample()
    await example.run_demonstration()


if __name__ == "__main__":
    asyncio.run(main())
