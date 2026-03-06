"""Dynamic gRPC configuration example with hot reload and profiles.

This script demonstrates the new dynamic configuration capabilities
including hot reload, environment profiles, feature flags, and
configuration API endpoints.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from omnimind_backend.grpc.config.dynamic.manager import DynamicConfigManager, get_config_manager
from omnimind_backend.grpc.config.dynamic.storage import create_config_storage
from omnimind_backend.grpc.config.dynamic.validator import ConfigValidator
from omnimind_backend.grpc.config.profiles import get_environment_loader
from omnimind_backend.grpc.config.features import get_feature_toggles, FeatureEvaluationContext
from omnimind_backend.grpc.config.dynamic.watcher import CombinedConfigWatcher
from omnimind_backend.grpc.config import GrpcConfig
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def example_dynamic_config_manager():
    """Example of dynamic configuration manager usage."""
    print("🔧 Dynamic Configuration Manager Example")
    print("=" * 60)
    
    try:
        # Create storage backend
        storage = create_config_storage("memory")
        
        # Create configuration manager
        config_manager = DynamicConfigManager(storage)
        
        # Initialize with default configuration
        initial_config = GrpcConfig(
            host="localhost",
            port=50051,
            enable_metrics=True,
            debug_mode=True,
            profile="development"
        )
        
        success = await config_manager.initialize(initial_config)
        print(f"   ✅ Configuration manager initialized: {success}")
        
        # Get current configuration
        current_config = await config_manager.get_current_config()
        if current_config:
            print(f"   📊 Current config: {current_config.host}:{current_config.port}")
            print(f"   🔧 Profile: {current_config.profile}")
            print(f"   📈 Metrics: {current_config.enable_metrics}")
            print(f"   🐛 Debug: {current_config.debug_mode}")
        
        # Subscribe to configuration changes
        def on_config_change(event):
            print(f"   🔄 Config changed: {event.snapshot.change_type.value}")
            print(f"      Version: {event.snapshot.version}")
            print(f"      Description: {event.snapshot.description}")
        
        subscriber_id = config_manager.subscribe_to_changes(on_config_change)
        print(f"   📝 Subscribed to changes: {subscriber_id}")
        
        # Test partial update
        print("\n   🧪 Testing partial configuration update...")
        updates = {
            "port": 50052,
            "max_connections": 200,
            "debug_mode": False
        }
        
        success = await config_manager.update_config(updates)
        print(f"   ✅ Update successful: {success}")
        
        # Get updated configuration
        updated_config = await config_manager.get_current_config()
        if updated_config:
            print(f"   📊 Updated config: {updated_config.host}:{updated_config.port}")
            print(f"   🔧 Max connections: {updated_config.max_connections}")
            print(f"   🐛 Debug: {updated_config.debug_mode}")
        
        # Test validation
        print("\n   🧪 Testing configuration validation...")
        invalid_updates = {
            "port": 99999,  # Invalid port
            "max_connections": -1,  # Invalid connections
        }
        
        validation_result = await config_manager.validator.validate_partial_update(invalid_updates)
        print(f"   ❌ Validation passed: {validation_result.is_valid}")
        print(f"   📝 Errors: {len(validation_result.errors)}")
        for error in validation_result.errors:
            print(f"      - {error.field}: {error.message}")
        
        # Get configuration history
        print("\n   📚 Configuration history:")
        history = await config_manager.get_config_history(limit=3)
        for i, snapshot in enumerate(history):
            print(f"      {i+1}. {snapshot['version']} - {snapshot['change_type']}")
            print(f"         {snapshot['description']}")
        
        # Get statistics
        stats = await config_manager.get_statistics()
        print(f"\n   📊 Manager statistics:")
        print(f"      Current version: {stats['current_version']}")
        print(f"      History size: {stats['history_size']}")
        print(f"      Subscribers: {stats['subscriber_count']}")
        
        # Cleanup
        config_manager.unsubscribe_from_changes(subscriber_id)
        print(f"\n   🧹 Unsubscribed: {subscriber_id}")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_environment_profiles():
    """Example of environment profile usage."""
    print("\n🌍 Environment Profiles Example")
    print("=" * 60)
    
    try:
        env_loader = get_environment_loader()
        
        # List available profiles
        profiles = env_loader.list_profiles()
        print(f"   📋 Available profiles: {len(profiles)}")
        for profile in profiles:
            print(f"      - {profile['name']}: {profile['description']}")
        
        # Test different profiles
        base_config = GrpcConfig()
        
        for profile_name in ["development", "production", "testing"]:
            print(f"\n   🧪 Testing {profile_name} profile...")
            
            profile_config = await env_loader.load_profile_config(profile_name, base_config)
            
            print(f"      🔧 Debug mode: {profile_config.debug_mode}")
            print(f"      🔒 Secure: {profile_config.secure}")
            print(f"      📈 Metrics: {profile_config.enable_metrics}")
            print(f"      🔌 Max connections: {profile_config.max_connections}")
            
            # Validate for environment
            issues = profile_config.validate_for_environment(profile_name)
            if issues:
                print(f"      ⚠️  Issues: {len(issues)}")
                for issue in issues:
                    print(f"         - {issue}")
            else:
                print(f"      ✅ Valid for {profile_name}")
        
        # Test profile inheritance
        print(f"\n   🧪 Testing profile inheritance...")
        staging_profile = env_loader.get_profile_info("staging")
        if staging_profile:
            print(f"      📋 Staging profile:")
            print(f"         Parent: {staging_profile['parent_profile']}")
            print(f"         Overrides: {len(staging_profile['overrides'])}")
            print(f"         Inherited: {len(staging_profile['inherited_overrides'])}")
        
        # Auto-detect environment
        detected_env = await env_loader.detect_environment()
        print(f"\n   🌍 Detected environment: {detected_env}")
        
        # Auto-load profile
        auto_config = await env_loader.auto_load_profile(base_config)
        print(f"   🤖 Auto-loaded profile: {auto_config.profile}")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_feature_flags():
    """Example of feature flags usage."""
    print("\n🚩 Feature Flags Example")
    print("=" * 60)
    
    try:
        feature_toggles = await get_feature_toggles()
        
        # List all feature flags
        flags = await feature_toggles.registry.get_all_flags()
        print(f"   🚩 Available flags: {len(flags)}")
        
        for flag_name, flag in flags.items():
            print(f"      - {flag_name}: {flag.current_state.value}")
            print(f"        {flag.description}")
        
        # Test feature evaluation
        print(f"\n   🧪 Testing feature evaluation...")
        
        test_flags = [
            "grpc_monitoring_enabled",
            "grpc_circuit_breaker_enabled",
            "grpc_compression_enabled",
            "grpc_tls_enabled"
        ]
        
        context = FeatureEvaluationContext(
            user_id="test-user-123",
            session_id="test-session-456",
            environment="development"
        )
        
        for flag_name in test_flags:
            enabled = await feature_toggles.is_enabled(flag_name, context)
            print(f"      🚩 {flag_name}: {'✅' if enabled else '❌'}")
        
        # Test percentage rollout
        print(f"\n   🧪 Testing percentage rollout...")
        
        # Set percentage rollout
        success = await feature_toggles.set_percentage_rollout("grpc_compression_enabled", 50.0)
        print(f"   ✅ Set 50% rollout: {success}")
        
        # Test with different contexts
        for i in range(5):
            test_context = FeatureEvaluationContext(
                user_id=f"user-{i}",
                session_id=f"session-{i}"
            )
            enabled = await feature_toggles.is_enabled("grpc_compression_enabled", test_context)
            print(f"      👤 User {i}: {'✅' if enabled else '❌'}")
        
        # Test feature dependencies
        print(f"\n   🧪 Testing feature dependencies...")
        
        # Disable monitoring (should disable circuit breaker)
        success = await feature_toggles.disable_flag("grpc_monitoring_enabled")
        print(f"   ✅ Disabled monitoring: {success}")
        
        # Check circuit breaker (should be disabled due to dependency)
        cb_enabled = await feature_toggles.is_enabled("grpc_circuit_breaker_enabled")
        print(f"   ⚡ Circuit breaker enabled: {cb_enabled} (should be False)")
        
        # Get configuration overrides
        print(f"\n   🔧 Configuration overrides from enabled features:")
        overrides = await feature_toggles.get_config_overrides()
        for key, value in overrides.items():
            print(f"      - {key}: {value}")
        
        # Get statistics
        stats = await feature_toggles.get_statistics()
        print(f"\n   📊 Feature flags statistics:")
        print(f"      Total flags: {stats['total_flags']}")
        print(f"      Enabled: {stats['enabled_flags']}")
        print(f"      Disabled: {stats['disabled_flags']}")
        print(f"      Percentage: {stats['percentage_flags']}")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_config_watcher():
    """Example of configuration watcher for hot reload."""
    print("\n👁️  Configuration Watcher Example")
    print("=" * 60)
    
    try:
        # Create configuration manager
        storage = create_config_storage("file", config_file="test_grpc_config.json")
        config_manager = DynamicConfigManager(storage)
        
        # Initialize
        initial_config = GrpcConfig(
            host="localhost",
            port=50051,
            enable_metrics=True
        )
        await config_manager.initialize(initial_config)
        
        # Create watcher
        from omnimind_backend.grpc.config.dynamic.watcher import ConfigWatcher, FileWatchConfig
        
        watch_config = FileWatchConfig(
            watch_directories={"."},
            file_patterns={"*.json", "*.yaml"},
            ignore_patterns={"*.pyc", "__pycache__"},
            check_interval=1.0,
            debounce_delay=2.0
        )
        
        watcher = ConfigWatcher(config_manager, watch_config)
        
        # Add change callback
        def on_file_change(change_type: str, timestamp: float):
            print(f"   🔄 File change detected: {change_type} at {timestamp}")
        
        watcher.add_change_callback(on_file_change)
        
        # Start watcher
        success = await watcher.start()
        print(f"   ✅ Watcher started: {success}")
        
        # Get watcher statistics
        stats = await watcher.get_statistics()
        print(f"   📊 Watcher stats:")
        print(f"      Running: {stats['running']}")
        print(f"      Watched files: {stats['watched_files']}")
        print(f"      Check interval: {stats['check_interval']}s")
        
        # Simulate configuration file change
        print(f"\n   🧪 Simulating configuration file change...")
        
        # Create a test config file
        test_config = {
            "host": "localhost",
            "port": 50053,
            "enable_metrics": True,
            "debug_mode": False,
            "max_connections": 300
        }
        
        import json
        with open("test_grpc_config.json", "w") as f:
            json.dump(test_config, f, indent=2)
        
        print(f"   📝 Created test config file")
        
        # Wait for watcher to detect change
        print(f"   ⏳ Waiting for file change detection...")
        await asyncio.sleep(3)
        
        # Check if configuration was reloaded
        current_config = await config_manager.get_current_config()
        if current_config and current_config.port == 50053:
            print(f"   ✅ Configuration reloaded successfully!")
            print(f"      New port: {current_config.port}")
            print(f"      New max connections: {current_config.max_connections}")
        else:
            print(f"   ⚠️  Configuration not reloaded (this is expected in this demo)")
        
        # Cleanup
        await watcher.stop()
        print(f"   🛑 Watcher stopped")
        
        # Remove test file
        import os
        if os.path.exists("test_grpc_config.json"):
            os.remove("test_grpc_config.json")
            print(f"   🗑️  Test file removed")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_integrated_dynamic_config():
    """Example of integrated dynamic configuration system."""
    print("\n🔗 Integrated Dynamic Configuration Example")
    print("=" * 60)
    
    try:
        # Create storage backend
        storage = create_config_storage("memory")
        
        # Initialize all components
        config_manager = DynamicConfigManager(storage)
        await config_manager.initialize()
        
        env_loader = get_environment_loader()
        feature_toggles = await get_feature_toggles()
        
        # Load dynamic configuration with profile and features
        print(f"   🔄 Loading dynamic configuration...")
        
        # Start with base config
        base_config = await config_manager.get_current_config()
        if not base_config:
            base_config = GrpcConfig()
        
        # Apply environment profile
        profile_config = await env_loader.load_profile_config("development", base_config)
        
        # Apply feature flags
        feature_overrides = await feature_toggles.get_config_overrides()
        final_config = profile_config.apply_feature_overrides(feature_overrides)
        
        print(f"   ✅ Dynamic configuration loaded:")
        print(f"      Profile: {final_config.profile}")
        print(f"      Host: {final_config.host}:{final_config.port}")
        print(f"      Metrics: {final_config.enable_metrics}")
        print(f"      Circuit breaker: {final_config.circuit_breaker_enabled}")
        print(f"      Debug: {final_config.debug_mode}")
        
        # Test configuration validation
        print(f"\n   🔍 Validating configuration...")
        
        validation_result = await config_manager.validator.validate_config(final_config)
        print(f"      Valid: {validation_result.is_valid}")
        
        if validation_result.warnings:
            print(f"      Warnings: {len(validation_result.warnings)}")
            for warning in validation_result.warnings[:3]:  # Show first 3
                print(f"         - {warning.field}: {warning.message}")
        
        # Test configuration update with validation
        print(f"\n   🧪 Testing validated update...")
        
        updates = {
            "port": 50054,
            "max_connections": 150,
            "enable_metrics": True
        }
        
        success = await config_manager.update_config(updates)
        print(f"      Update successful: {success}")
        
        if success:
            updated_config = await config_manager.get_current_config()
            print(f"      New configuration applied:")
            print(f"         Port: {updated_config.port}")
            print(f"         Max connections: {updated_config.max_connections}")
        
        # Test feature flag change
        print(f"\n   🚩 Testing feature flag change...")
        
        # Enable compression feature
        success = await feature_toggles.enable_flag("grpc_compression_enabled")
        print(f"      Compression enabled: {success}")
        
        # Get updated configuration overrides
        new_overrides = await feature_toggles.get_config_overrides()
        print(f"      Updated overrides: {len(new_overrides)}")
        
        # Test profile switch
        print(f"\n   🌍 Testing profile switch...")
        
        production_config = await env_loader.load_profile_config("production", base_config)
        print(f"      Production config loaded:")
        print(f"         Secure: {production_config.secure}")
        print(f"         Debug: {production_config.debug_mode}")
        print(f"         Max connections: {production_config.max_connections}")
        
        # Validate production config
        prod_issues = production_config.validate_for_environment("production")
        if prod_issues:
            print(f"      Production issues: {len(prod_issues)}")
        else:
            print(f"      ✅ Production config is valid")
        
        # Get comprehensive statistics
        print(f"\n   📊 System statistics:")
        
        config_stats = await config_manager.get_statistics()
        feature_stats = await feature_toggles.get_statistics()
        
        print(f"      Config manager:")
        print(f"         Version: {config_stats['current_version']}")
        print(f"         History: {config_stats['history_size']} entries")
        print(f"         Subscribers: {config_stats['subscriber_count']}")
        
        print(f"      Feature flags:")
        print(f"         Total: {feature_stats['total_flags']}")
        print(f"         Enabled: {feature_stats['enabled_flags']}")
        print(f"         Disabled: {feature_stats['disabled_flags']}")
        
        print(f"\n   ✅ Integrated dynamic configuration system working!")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def main():
    """Run all dynamic configuration examples."""
    print("🎯 OmniMind Dynamic gRPC Configuration Examples")
    print("=" * 70)
    print("This script demonstrates the dynamic configuration system with")
    print("hot reload, environment profiles, feature flags, and validation.")
    print()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run examples
    await example_dynamic_config_manager()
    await example_environment_profiles()
    await example_feature_flags()
    await example_config_watcher()
    await example_integrated_dynamic_config()
    
    print("\n✅ Dynamic Configuration Examples Completed!")
    print("\n🚀 Next Steps:")
    print("1. Start the application: python -m omnimind_backend.main")
    print("2. Access configuration API: http://localhost:8000/api/v1/config")
    print("3. View feature flags: http://localhost:8000/api/v1/config/features")
    print("4. Check environment profiles: http://localhost:8000/api/v1/config/profiles")
    print("5. Monitor configuration changes via logs")
    print("\n🔧 Configuration Management:")
    print("- Use PUT /api/v1/config to update configuration")
    print("- Use POST /api/v1/config/reload to trigger reload")
    print("- Use GET /api/v1/config/history to view changes")
    print("- Use POST /api/v1/config/rollback/{version} to rollback")
    print("\n🚩 Feature Flag Management:")
    print("- Use PUT /api/v1/config/features/{flag} to toggle features")
    print("- Use GET /api/v1/config/features/{flag}/enabled to check status")
    print("- Configure percentage rollouts and conditions")
    print("\n🌍 Environment Profiles:")
    print("- Use POST /api/v1/config/profiles/{name}/apply to apply profile")
    print("- Profiles: development, testing, staging, production, local")
    print("- Automatic profile detection based on APP_ENV")


if __name__ == "__main__":
    asyncio.run(main())
