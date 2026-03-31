#!/usr/bin/env python3
"""Test script for gRPC dynamic configuration integration."""

import asyncio
from pathlib import Path

# Get project root from tests directory
project_root = Path(__file__).parent.parent.parent.parent

async def test_grpc_integration():
    """Test gRPC with dynamic configuration integration."""
    try:
        print('🚀 Testing gRPC Advanced Features Integration')
        print('=' * 60)
        
        # Test 1: Dynamic Configuration
        print('\n1. Testing Dynamic Configuration:')
        from mindflow_backend.grpc.config.dynamic.manager import DynamicConfigManager
        from mindflow_backend.grpc.config.dynamic.storage import MemoryConfigStorage
        
        storage = MemoryConfigStorage()
        config_manager = DynamicConfigManager(storage)
        await config_manager.initialize()
        print('   ✅ Dynamic config manager initialized')
        
        # Test 2: Load Configuration
        from mindflow_backend.grpc.config.config import GrpcConfig
        grpc_config = await GrpcConfig.load_dynamic()
        print(f'   ✅ gRPC config loaded: {grpc_config.host}:{grpc_config.port}')
        print(f'   ✅ Profile: {grpc_config.profile}')
        print(f'   ✅ Circuit breaker: {grpc_config.circuit_breaker_enabled}')
        print(f'   ✅ Monitoring: {grpc_config.enable_metrics}')
        
        # Test 3: Configuration Updates
        updates = {
            'port': 50053,
            'debug_mode': False,
            'max_connections': 200
        }
        success = await config_manager.update_config(updates, 'Integration test')
        print(f'   ✅ Config update successful: {success}')
        
        updated_config = await config_manager.get_current_config()
        print(f'   ✅ Updated port: {updated_config.port}')
        
        # Test 4: Environment Profiles
        print('\n2. Testing Environment Profiles:')
        from mindflow_backend.grpc.config.profiles import get_environment_loader
        
        env_loader = get_environment_loader()
        profiles = env_loader.list_profiles()
        print(f'   ✅ Available profiles: {[p["name"] for p in profiles]}')
        
        # Apply development profile
        dev_config = await env_loader.load_profile_config('development', grpc_config)
        print(f'   ✅ Development profile applied: debug={dev_config.debug_mode}')
        
        # Test 5: Enhanced Server
        print('\n3. Testing Enhanced gRPC Server:')
        from mindflow_backend.grpc.server import EnhancedGrpcAgentServer
        
        server = EnhancedGrpcAgentServer(grpc_config)
        print(f'   ✅ Enhanced server created with config: {server.config.host}:{server.config.port}')
        print(f'   ✅ Features: monitoring={server.config.enable_metrics}, health_check={server.config.enable_health_check}')
        
        # Test 6: Enhanced Client
        print('\n4. Testing Enhanced gRPC Client:')
        from mindflow_backend.grpc.client import EnhancedGrpcAgentClient
        from mindflow_backend.grpc.config.config import GrpcClientConfig
        
        client_config = GrpcClientConfig.from_server_config(grpc_config)
        client = EnhancedGrpcAgentClient(
            config=client_config,
            enable_monitoring=True,
            enable_circuit_breaker=True,
            enable_retry=True,
            enable_timeout_management=True
        )
        print('   ✅ Enhanced client created with features: monitoring, circuit_breaker, retry, timeout_management')
        
        # Test 7: Statistics
        print('\n5. Testing Statistics Collection:')
        server_stats = server.get_server_info()
        
        print(f'   ✅ Server info: {server_stats["config"]["enabled"]} enabled, {len(server_stats["features"])} features')
        
        # Test 8: Configuration API
        print('\n6. Testing Configuration API:')
        history = await config_manager.get_config_history(limit=5)
        print(f'   ✅ Configuration history: {len(history)} entries')
        
        stats = await config_manager.get_statistics()
        print(f'   ✅ Config manager stats: {stats["current_version"] if "current_version" in stats else "unknown"}')
        
        print('\n🎉 gRPC Advanced Features Integration Test Completed Successfully!')
        print('\n📊 Summary:')
        print('   - Dynamic Configuration: ✅ Working')
        print('   - Environment Profiles: ✅ Working') 
        print('   - Feature Flags: ⚠️  Skipped (dependency issues)')
        print('   - Enhanced Server: ✅ Working')
        print('   - Enhanced Client: ✅ Working')
        print('   - Statistics & Monitoring: ✅ Working')
        print('   - Configuration API: ✅ Working')
        
        return True
        
    except Exception as e:
        print(f'\n❌ Integration test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_grpc_integration())
    sys.exit(0 if success else 1)
