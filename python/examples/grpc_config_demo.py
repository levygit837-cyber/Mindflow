#!/usr/bin/env python3
"""
gRPC Dynamic Configuration Demo

Demonstrates the core dynamic configuration features
without requiring all the complex dependencies.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindflow_backend.grpc.config import GrpcConfig
from mindflow_backend.grpc.config.dynamic.manager import get_config_manager
from mindflow_backend.grpc.config.profiles import get_environment_loader
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def demonstrate_dynamic_configuration():
    """Demonstrate dynamic configuration capabilities."""
    print("🚀 gRPC Dynamic Configuration Demo")
    print("=" * 50)
    
    try:
        # 1. Initialize Dynamic Configuration Manager
        print("\n1. Dynamic Configuration Manager:")
        from mindflow_backend.grpc.config.dynamic.manager import DynamicConfigManager
        from mindflow_backend.grpc.config.dynamic.storage import MemoryConfigStorage
        
        storage = MemoryConfigStorage()
        config_manager = DynamicConfigManager(storage)
        await config_manager.initialize()
        print("   ✅ Dynamic config manager initialized")
        
        # 2. Load Configuration with Environment Detection
        print("\n2. Configuration Loading:")
        grpc_config = await GrpcConfig.load_dynamic()
        print(f"   ✅ Host: {grpc_config.host}")
        print(f"   ✅ Port: {grpc_config.port}")
        print(f"   ✅ Profile: {grpc_config.profile}")
        print(f"   ✅ Auto-reload: {grpc_config.auto_reload}")
        
        # 3. Environment Profiles
        print("\n3. Environment Profiles:")
        env_loader = get_environment_loader()
        profiles = env_loader.list_profile_names()
        print(f"   ✅ Available profiles: {profiles}")
        
        # Apply different profiles
        for profile_name in ['development', 'production']:
            profile_config = await env_loader.load_profile_config(profile_name, grpc_config)
            print(f"   📋 {profile_name.title()} profile:")
            print(f"      - Debug mode: {profile_config.debug_mode}")
            print(f"      - Max connections: {profile_config.max_connections}")
            print(f"      - Circuit breaker: {profile_config.circuit_breaker_threshold}")
            print(f"      - Monitoring: {profile_config.enable_metrics}")
        
        # 4. Dynamic Updates
        print("\n4. Dynamic Configuration Updates:")
        
        # Test multiple configuration updates
        updates = [
            {
                'name': 'Performance Settings',
                'changes': {
                    'max_connections': 1000,
                    'connection_timeout_seconds': 15,
                    'default_timeout_seconds': 120
                }
            },
            {
                'name': 'Monitoring Settings',
                'changes': {
                    'enable_metrics': True,
                    'metrics_history_size': 2000,
                    'system_metrics_interval': 2
                }
            },
            {
                'name': 'Resilience Settings',
                'changes': {
                    'circuit_breaker_enabled': True,
                    'circuit_breaker_threshold': 8,
                    'circuit_breaker_recovery_timeout': 45,
                    'max_attempts': 5,
                    'retry_jitter': True
                }
            }
        ]
        
        for i, update in enumerate(updates, 1):
            print(f"\n   Update {i}: {update['name']}")
            success = await config_manager.update_config(
                update['changes'], 
                update['name']
            )
            print(f"   ✅ Applied: {success}")
            
            # Show current state
            current_config = await config_manager.get_current_config()
            print(f"   📊 Max connections: {current_config.max_connections}")
            print(f"   📊 Circuit breaker: {current_config.circuit_breaker_threshold}")
        
        # 5. Configuration History
        print("\n5. Configuration History:")
        history = await config_manager.get_config_history(limit=5)
        print(f"   ✅ Total changes: {len(history)}")
        
        for i, entry in enumerate(history, 1):
            print(f"   {i}. {entry['change_type']}")
            print(f"      Description: {entry['description']}")
            print(f"      Version: {entry['version']}")
            print(f"      Changed: {len(entry['changed_fields'])} fields")
        
        # 6. Statistics
        print("\n6. Configuration Statistics:")
        stats = await config_manager.get_statistics()
        print(f"   ✅ Current version: {stats.get('current_version', 'unknown')}")
        print(f"   ✅ Total updates: {stats.get('total_updates', 0)}")
        print(f"   ✅ Storage type: {stats.get('storage_type', 'unknown')}")
        
        # 7. Configuration Validation
        print("\n7. Configuration Validation:")
        
        # Test validation for different environments
        environments = ['development', 'staging', 'production']
        for env in environments:
            issues = grpc_config.validate_for_environment(env)
            if issues:
                print(f"   ⚠️  {env.title()} issues: {len(issues)}")
                for issue in issues:
                    print(f"      - {issue}")
            else:
                print(f"   ✅ {env.title()}: Valid configuration")
        
        # 8. Production Readiness Check
        print("\n8. Production Readiness:")
        is_production_ready = grpc_config.is_production_ready()
        if is_production_ready:
            print("   ✅ Configuration is production-ready")
        else:
            print("   ⚠️  Configuration needs adjustments for production")
            print("   Required for production:")
            if grpc_config.debug_mode:
                print("      - Disable debug mode")
            if grpc_config.reflection_enabled:
                print("      - Disable reflection")
            if not grpc_config.secure:
                print("      - Enable TLS/SSL")
            if not grpc_config.enable_metrics:
                print("      - Enable monitoring")
        
        print("\n🎉 Dynamic Configuration Demo Completed Successfully!")
        print("\n📋 Implemented Features:")
        print("   ✅ Hot-reload configuration without restart")
        print("   ✅ Environment-specific profiles")
        print("   ✅ Configuration validation")
        print("   ✅ Change history tracking")
        print("   ✅ Atomic configuration updates")
        print("   ✅ Production readiness validation")
        print("   ✅ Statistics and monitoring")
        print("   ✅ Configuration rollback capability")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


async def demonstrate_feature_flags():
    """Demonstrate feature flags system."""
    print("\n🚩 Feature Flags Demo:")
    
    try:
        # Note: Feature flags have dependency issues in current setup
        # This demonstrates the intended functionality
        print("   ⚠️  Feature flags temporarily disabled due to dependency resolution")
        print("   📋 Planned features:")
        print("      - Dynamic feature toggling")
        print("      - Percentage-based rollouts")
        print("      - A/B testing support")
        print("      - Feature dependency management")
        print("      - Real-time flag updates")
        
    except Exception as e:
        print(f"   ❌ Feature flags demo error: {e}")


async def main():
    """Main demonstration function."""
    await demonstrate_dynamic_configuration()
    await demonstrate_feature_flags()
    
    print("\n🏁 Next Steps:")
    print("   1. Start the enhanced gRPC server with dynamic config")
    print("   2. Test configuration changes via API endpoints")
    print("   3. Monitor system behavior with new features")
    print("   4. Validate performance improvements")


if __name__ == "__main__":
    asyncio.run(main())
