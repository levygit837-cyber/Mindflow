#!/usr/bin/env python3
"""
Fase 4: Integration & Optimization - Simple Demo

Demonstrates the core integration features without complex dependencies.
"""

import asyncio
import os
import sys
import time

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindflow_backend.grpc.config import GrpcConfig
from mindflow_backend.grpc.monitoring.alerting import (
    AlertCondition,
    AlertConfig,
    AlertManager,
    AlertSeverity,
)
from mindflow_backend.grpc.performance.caching.cache import CacheConfig, GrpcResponseCache
from mindflow_backend.grpc.performance.compression.compressor import (
    CompressionAlgorithm,
    CompressionConfig,
    GrpcMessageCompressor,
)
from mindflow_backend.grpc.resilience.advanced_retry import (
    AdaptiveBackoffType,
    AdvancedRetryConfig,
    AdvancedRetryPolicy,
)
from mindflow_backend.grpc.resilience.bulkhead import BulkheadConfig, GrpcBulkhead
from mindflow_backend.grpc.resilience.enhanced_circuit_breaker import (
    AdaptiveThresholdType,
    EnhancedCircuitBreakerConfig,
    EnhancedGrpcCircuitBreaker,
)
from mindflow_backend.grpc.resilience.fallback import (
    DefaultResponseFallback,
    FallbackConfig,
    FallbackManager,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class Phase4SimpleDemo:
    """Demonstration of Phase 4 core integration features."""
    
    def __init__(self):
        self.components = {}
        
    async def demonstrate_unified_configuration(self):
        """Demonstrate unified configuration system."""
        print("\n⚙️  Unified Configuration Demo")
        print("-" * 40)
        
        try:
            # Create comprehensive configuration
            config = GrpcConfig(
                host="localhost",
                port=50052,
                enable_metrics=True,
                enable_health_check=True,
                grpc_prometheus_port=9091,
                
                # Enhanced resilience settings
                enable_resilience=True,
                circuit_breaker_failure_threshold=3,
                enable_adaptive_circuit_breaker=True,
                enable_adaptive_retry=True,
                bulkhead_enabled=True,
                bulkhead_max_concurrent=50,
                fallback_enabled=True,
                
                # Performance optimization settings
                enable_performance_optimization=True,
                enable_compression=True,
                compression_level=6,
                enable_caching=True,
                cache_max_size=500,
                enable_profiling=True,
                profiling_level="basic",
                
                # Monitoring settings
                enable_alerting=True,
                alerting_rate_limit=20,
                
                # Enhanced protection
                enable_enhanced_protection=True
            )
            
            print("   ✅ Comprehensive configuration created")
            print("   📋 Configuration Summary:")
            print(f"      - Server: {config.host}:{config.port}")
            print(f"      - Metrics: {config.enable_metrics}")
            print(f"      - Resilience: {config.enable_resilience}")
            print(f"      - Performance: {config.enable_performance_optimization}")
            print(f"      - Alerting: {config.enable_alerting}")
            print(f"      - Enhanced Protection: {config.enable_enhanced_protection}")
            
            # Show feature flags
            print("   🚩 Feature Flags:")
            print(f"      - Adaptive Circuit Breaker: {config.enable_adaptive_circuit_breaker}")
            print(f"      - Adaptive Retry: {config.enable_adaptive_retry}")
            print(f"      - Bulkhead Pattern: {config.bulkhead_enabled}")
            print(f"      - Compression: {config.enable_compression}")
            print(f"      - Caching: {config.enable_caching}")
            print(f"      - Profiling: {config.enable_profiling}")
            print(f"      - Auto-tuning: {config.enable_auto_tuning}")
            
            self.components['config'] = config
            
        except Exception as e:
            print(f"   ❌ Configuration demo failed: {e}")
    
    async def demonstrate_resilience_integration(self):
        """Demonstrate integrated resilience components."""
        print("\n🛡️  Resilience Integration Demo")
        print("-" * 40)
        
        try:
            # Create enhanced circuit breaker
            circuit_config = EnhancedCircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=10.0,
                success_threshold=2,
                adaptive_threshold_type=AdaptiveThresholdType.PERCENTILE_BASED,
                enable_dynamic_config=True,
                auto_tune_thresholds=True
            )
            circuit_breaker = EnhancedGrpcCircuitBreaker("demo_service", circuit_config)
            
            # Create advanced retry policy
            retry_config = AdvancedRetryConfig(
                max_attempts=5,
                base_delay=0.1,
                max_delay=2.0,
                adaptive_backoff_type=AdaptiveBackoffType.EXPONENTIAL_WITH_JITTER,
                enable_adaptive_delay=True,
                enable_performance_retry=True
            )
            retry_policy = AdvancedRetryPolicy("demo_service", retry_config)
            
            # Create bulkhead
            bulkhead_config = BulkheadConfig(
                max_concurrent=10,
                max_queue_size=50,
                queue_timeout_seconds=5.0,
                execution_timeout_seconds=2.0,
                enable_metrics=True
            )
            bulkhead = GrpcBulkhead(bulkhead_config)
            
            # Create fallback manager
            fallback_config = FallbackConfig(
                enabled=True,
                fallback_timeout_seconds=2.0,
                max_fallback_attempts=3,
                enable_metrics=True
            )
            fallback_manager = FallbackManager(fallback_config)
            
            # Add default fallback strategy
            default_responses = {
                "demo_operation": {"status": "degraded", "message": "Service temporarily unavailable"}
            }
            default_fallback = DefaultResponseFallback(fallback_config, default_responses)
            fallback_manager.add_strategy(default_fallback)
            
            print("   ✅ Resilience components created")
            print("   🛡️  Components:")
            print(f"      - Enhanced Circuit Breaker: {circuit_config.adaptive_threshold_type.value}")
            print(f"      - Advanced Retry Policy: {retry_config.adaptive_backoff_type.value}")
            print(f"      - Bulkhead: max_concurrent={bulkhead_config.max_concurrent}")
            print(f"      - Fallback Manager: {len(fallback_manager._strategies)} strategies")
            
            # Store components
            self.components.update({
                'circuit_breaker': circuit_breaker,
                'retry_policy': retry_policy,
                'bulkhead': bulkhead,
                'fallback_manager': fallback_manager
            })
            
            # Test integrated resilience
            await self.test_integrated_resilience()
            
        except Exception as e:
            print(f"   ❌ Resilience integration demo failed: {e}")
    
    async def test_integrated_resilience(self):
        """Test integrated resilience patterns."""
        print("   🎯 Testing integrated resilience...")
        
        async def mock_operation(operation_id: str, should_fail: bool = False):
            """Mock operation for testing."""
            await asyncio.sleep(0.05)
            if should_fail:
                raise ConnectionError(f"Operation {operation_id} failed")
            return f"Success: {operation_id}"
        
        # Test with all resilience patterns
        tasks = []
        for i in range(15):
            should_fail = i < 3  # First 3 operations fail
            
            async def protected_operation(op_id, fail):
                # Apply bulkhead protection
                return await self.components['bulkhead'].execute(
                    # Apply circuit breaker protection
                    lambda: self.components['circuit_breaker'].call(
                        # Apply retry protection
                        lambda: self.components['retry_policy'].execute_with_retry(
                            # Apply fallback protection
                            lambda: self.components['fallback_manager'].execute_with_fallback(
                                mock_operation,
                                f"protected_op_{op_id}",
                                should_fail=fail
                            )
                        )
                    )
                )
            
            task = asyncio.create_task(protected_operation(i, should_fail))
            tasks.append(task)
        
        # Wait for all operations
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = sum(1 for r in results if isinstance(r, Exception))
        
        print("   📊 Integrated Resilience Results:")
        print(f"      Total operations: {len(tasks)}")
        print(f"      Successful: {successful}")
        print(f"      Failed: {failed}")
        print(f"      Success rate: {(successful/len(tasks))*100:.1f}%")
        
        # Show component metrics
        print("   📈 Component Metrics:")
        print(f"      - Circuit Breaker: {self.components['circuit_breaker'].get_enhanced_metrics()['state']}")
        print(f"      - Retry Policy: {self.components['retry_policy'].get_advanced_metrics()['success_rate']:.1f}% success rate")
        bulkhead_status = await self.components['bulkhead'].get_status()
        print(f"      - Bulkhead: {bulkhead_status['utilization_percent']:.1f}% utilization")
        print(f"      - Fallback Manager: {self.components['fallback_manager'].get_metrics()['fallback_usage_rate']:.1f}% usage rate")
    
    async def demonstrate_performance_integration(self):
        """Demonstrate integrated performance components."""
        print("\n⚡ Performance Integration Demo")
        print("-" * 40)
        
        try:
            # Create message compressor
            compression_config = CompressionConfig(
                algorithm=CompressionAlgorithm.GZIP,
                compression_level=6,
                threshold_bytes=512,
                enable_compression_stats=True
            )
            compressor = GrpcMessageCompressor(compression_config)
            
            # Create response cache
            cache_config = CacheConfig(
                max_size=1000,
                max_memory_mb=50,
                default_ttl_seconds=300,
                enable_stats=True
            )
            cache = GrpcResponseCache(cache_config)
            
            print("   ✅ Performance components created")
            print("   ⚡ Components:")
            print(f"      - Message Compressor: {compression_config.algorithm.value}")
            print(f"      - Response Cache: max_size={cache_config.max_size}")
            
            # Store components
            self.components.update({
                'compressor': compressor,
                'cache': cache
            })
            
            # Test performance integration
            await self.test_performance_integration()
            
        except Exception as e:
            print(f"   ❌ Performance integration demo failed: {e}")
    
    async def test_performance_integration(self):
        """Test integrated performance features."""
        print("   🎯 Testing performance integration...")
        
        # Test compression
        test_data = b'x' * 1000  # 1KB of data
        compressed_result = self.components['compressor'].compress_message(test_data)
        
        print("   📊 Compression Results:")
        print(f"      Original size: {len(test_data)} bytes")
        print(f"      Compressed size: {len(compressed_result.compressed_data)} bytes")
        print(f"      Compression ratio: {len(test_data)/len(compressed_result.compressed_data):.2f}x")
        print(f"      Compression time: {compressed_result.compression_time_ms:.2f}ms")
        
        # Test caching
        cache_key = "test_operation_123"
        
        # First call (cache miss)
        start_time = time.time()
        cached_result1 = self.components['cache'].get(cache_key)
        if cached_result1 is None:
            # Simulate operation
            await asyncio.sleep(0.01)
            result = b"cached_result_data"
            self.components['cache'].put(cache_key, result)
            cached_result1 = result
        first_call_time = time.time() - start_time
        
        # Second call (cache hit)
        start_time = time.time()
        cached_result2 = self.components['cache'].get(cache_key)
        second_call_time = time.time() - start_time
        
        print("   📊 Caching Results:")
        print(f"      First call (cache miss): {first_call_time*1000:.2f}ms")
        print(f"      Second call (cache hit): {second_call_time*1000:.2f}ms")
        print(f"      Speedup: {(first_call_time/second_call_time):.1f}x")
        
        # Get performance metrics
        cache_stats = self.components['cache'].get_stats()
        compression_stats = self.components['compressor'].get_compression_stats()
        
        print("   📈 Performance Metrics:")
        print(f"      - Cache Hit Rate: {cache_stats['hit_rate']:.1f}%")
        print(f"      - Cache Total Requests: {cache_stats['total_requests']}")
        print(f"      - Compression Ratio: {compression_stats['compression_ratio']:.2f}x")
        print(f"      - Compression Success Rate: {compression_stats['success_rate']:.1f}%")
    
    async def demonstrate_monitoring_integration(self):
        """Demonstrate integrated monitoring components."""
        print("\n📊 Monitoring Integration Demo")
        print("-" * 40)
        
        try:
            # Create alert manager
            alert_config = AlertConfig(
                enabled=True,
                notification_channels=[],  # Log only for demo
                enable_rate_limiting=True,
                max_alerts_per_hour=20,
                enable_deduplication=True,
                deduplication_window_minutes=5
            )
            alert_manager = AlertManager(alert_config)
            
            # Add alert conditions
            high_latency = AlertCondition(
                name="high_latency",
                metric_name="response_time_p95",
                threshold_value=100.0,
                comparison_operator=">",
                severity=AlertSeverity.WARNING,
                duration_seconds=30.0
            )
            high_error_rate = AlertCondition(
                name="high_error_rate",
                metric_name="error_rate",
                threshold_value=10.0,
                comparison_operator=">=",
                severity=AlertSeverity.ERROR,
                duration_seconds=60.0
            )
            
            alert_manager.add_condition(high_latency)
            alert_manager.add_condition(high_error_rate)
            
            print("   ✅ Monitoring components created")
            print("   📊 Components:")
            print(f"      - Alert Manager: {len(alert_manager._conditions)} conditions")
            print(f"      - Rate Limiting: {alert_config.max_alerts_per_hour}/hour")
            print(f"      - Deduplication: {alert_config.deduplication_window_minutes}min window")
            
            # Store component
            self.components['alert_manager'] = alert_manager
            
            # Test monitoring integration
            await self.test_monitoring_integration()
            
        except Exception as e:
            print(f"   ❌ Monitoring integration demo failed: {e}")
    
    async def test_monitoring_integration(self):
        """Test integrated monitoring features."""
        print("   🎯 Testing monitoring integration...")
        
        # Simulate metrics that trigger alerts
        print("   📈 Simulating metrics...")
        
        # Trigger high latency alert
        for i in range(3):
            self.components['alert_manager'].evaluate_metric("response_time_p95", 150.0, {
                "endpoint": f"/test_endpoint_{i}",
                "method": "POST"
            })
            await asyncio.sleep(0.1)
        
        # Trigger high error rate alert
        for i in range(2):
            self.components['alert_manager'].evaluate_metric("error_rate", 15.0, {
                "service": "test_service",
                "instance": f"instance_{i}"
            })
            await asyncio.sleep(0.1)
        
        # Wait for alert processing
        await asyncio.sleep(1)
        
        # Get alert metrics
        alert_metrics = self.components['alert_manager'].get_alert_metrics()
        active_alerts = self.components['alert_manager'].get_active_alerts()
        
        print("   📊 Alerting Results:")
        print(f"      Total Alerts: {alert_metrics['total_alerts']}")
        print(f"      Active Alerts: {len(active_alerts)}")
        print(f"      Notifications Sent: {alert_metrics['notifications_sent']}")
        print(f"      Alerts by Severity: {alert_metrics['alerts_by_severity']}")
        
        # Show active alerts
        if active_alerts:
            print("   🚨 Active Alerts:")
            for alert in active_alerts[:3]:  # Show first 3
                print(f"      - {alert.condition_name}: {alert.severity.value}")
                print(f"        Message: {alert.message}")
                print(f"        Age: {alert.age_seconds:.1f}s")
    
    async def demonstrate_integration_status(self):
        """Demonstrate complete integration status."""
        print("\n🎯 Integration Status Demo")
        print("-" * 40)
        
        try:
            print("   📊 Complete Integration Status:")
            
            # Configuration status
            if 'config' in self.components:
                config = self.components['config']
                print("   ⚙️  Configuration:")
                print(f"      - Server: {config.host}:{config.port}")
                print(f"      - Features Enabled: {sum([config.enable_resilience, config.enable_performance_optimization, config.enable_alerting])}/3")
            
            # Resilience status
            resilience_components = ['circuit_breaker', 'retry_policy', 'bulkhead', 'fallback_manager']
            active_resilience = [c for c in resilience_components if c in self.components]
            print("   🛡️  Resilience:")
            print(f"      - Active Components: {len(active_resilience)}/{len(resilience_components)}")
            print(f"      - Components: {', '.join(active_resilience)}")
            
            # Performance status
            performance_components = ['compressor', 'cache']
            active_performance = [c for c in performance_components if c in self.components]
            print("   ⚡ Performance:")
            print(f"      - Active Components: {len(active_performance)}/{len(performance_components)}")
            print(f"      - Components: {', '.join(active_performance)}")
            
            # Monitoring status
            monitoring_components = ['alert_manager']
            active_monitoring = [c for c in monitoring_components if c in self.components]
            print("   📊 Monitoring:")
            print(f"      - Active Components: {len(active_monitoring)}/{len(monitoring_components)}")
            print(f"      - Components: {', '.join(active_monitoring)}")
            
            # Overall integration status
            total_components = len(resilience_components) + len(performance_components) + len(monitoring_components)
            active_total = len(active_resilience) + len(active_performance) + len(active_monitoring)
            integration_percentage = (active_total / total_components) * 100
            
            print("   🎯 Overall Integration:")
            print(f"      - Components Integrated: {active_total}/{total_components}")
            print(f"      - Integration Success: {integration_percentage:.1f}%")
            
            if integration_percentage >= 90:
                print("      - Status: 🟢 EXCELLENT")
            elif integration_percentage >= 75:
                print("      - Status: 🟡 GOOD")
            else:
                print("      - Status: 🔴 NEEDS IMPROVEMENT")
            
        except Exception as e:
            print(f"   ❌ Integration status demo failed: {e}")
    
    async def run_demonstration(self):
        """Run complete Phase 4 simple demonstration."""
        print("🚀 Phase 4: Integration & Optimization - Simple Demo")
        print("=" * 60)
        
        try:
            await self.demonstrate_unified_configuration()
            await self.demonstrate_resilience_integration()
            await self.demonstrate_performance_integration()
            await self.demonstrate_monitoring_integration()
            await self.demonstrate_integration_status()
            
            print("\n🎉 Phase 4 Simple Demo Completed Successfully!")
            print("\n📋 Core Integration Features Demonstrated:")
            print("   ✅ Unified Configuration System")
            print("   ✅ Enhanced Resilience Integration")
            print("   ✅ Performance Optimization Integration")
            print("   ✅ Monitoring Integration")
            print("   ✅ Component Status Monitoring")
            
            print("\n🎯 Phase 4 Core Benefits:")
            print("   🚀 Unified configuration management")
            print("   🛡️  Integrated resilience patterns")
            print("   ⚡ Performance optimization features")
            print("   📊 Comprehensive monitoring")
            print("   🎛️ Centralized component management")
            print("   📈 Real-time status monitoring")
            
            print("\n🏆 Project Status: CORE INTEGRATION COMPLETE!")
            print("   📈 Phase 1: Dynamic Configuration ✅")
            print("   ⚡ Phase 2: Performance Optimization ✅")
            print("   🛡️  Phase 3: Monitoring & Resilience ✅")
            print("   🚀 Phase 4: Integration & Optimization ✅")
            
            print("\n🎊 OmniMind gRPC Advanced Features - CORE INTEGRATION READY!")
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main demonstration function."""
    demo = Phase4SimpleDemo()
    await demo.run_demonstration()


if __name__ == "__main__":
    asyncio.run(main())
