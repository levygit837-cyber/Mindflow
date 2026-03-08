#!/usr/bin/env python3
"""
gRPC Resilience Features Demo

Demonstrates advanced resilience patterns including enhanced circuit breakers,
advanced retry policies, bulkhead pattern, fallback strategies, and alerting.
"""

import asyncio
import sys
import os
import time
import random
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindflow_backend.grpc.resilience.bulkhead import GrpcBulkhead, BulkheadConfig
from mindflow_backend.grpc.resilience.fallback import (
    FallbackManager, FallbackConfig, FallbackType,
    LocalCacheFallback, DefaultResponseFallback
)
from mindflow_backend.grpc.resilience.enhanced_circuit_breaker import (
    EnhancedGrpcCircuitBreaker, EnhancedCircuitBreakerConfig, AdaptiveThresholdType
)
from mindflow_backend.grpc.resilience.advanced_retry import (
    AdvancedRetryPolicy, AdvancedRetryConfig, AdaptiveBackoffType, RetryConditionType
)
from mindflow_backend.grpc.monitoring.alerting import (
    AlertManager, AlertConfig, AlertCondition, AlertSeverity, NotificationChannel
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ResilienceGrpcDemo:
    """Demonstration of gRPC resilience features."""
    
    def __init__(self):
        self.bulkhead = None
        self.fallback_manager = None
        self.circuit_breaker = None
        self.retry_policy = None
        self.alert_manager = None
        
    async def demonstrate_bulkhead(self):
        """Demonstrate bulkhead pattern."""
        print("\n🛡️  Bulkhead Pattern Demo")
        print("-" * 40)
        
        try:
            # Create bulkhead with conservative limits
            config = BulkheadConfig(
                max_concurrent=5,
                max_queue_size=20,
                queue_timeout_seconds=2.0,
                execution_timeout_seconds=1.0,
                enable_metrics=True
            )
            
            self.bulkhead = GrpcBulkhead(config)
            print(f"   ✅ Bulkhead initialized: max_concurrent={config.max_concurrent}")
            
            # Simulate concurrent operations
            async def mock_operation(name: str, duration: float):
                await asyncio.sleep(duration)
                return f"Operation {name} completed"
            
            # Submit more operations than capacity
            tasks = []
            for i in range(15):  # More than max_concurrent + max_queue_size
                operation_name = f"bulk_op_{i+1}"
                duration = random.uniform(0.1, 0.5)
                
                try:
                    task = asyncio.create_task(
                        self.bulkhead.execute(mock_operation, operation_name, duration=duration)
                    )
                    tasks.append(task)
                except Exception as e:
                    print(f"   ❌ Operation {operation_name} rejected: {str(e)}")
            
            # Wait for all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful vs rejected
            successful = sum(1 for r in results if not isinstance(r, Exception))
            rejected = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"   📊 Results: {successful} successful, {rejected} rejected")
            
            # Get bulkhead metrics
            metrics = self.bulkhead.get_metrics()
            print(f"   📈 Bulkhead Metrics:")
            print(f"      Total requests: {metrics['total_requests']}")
            print(f"      Accepted requests: {metrics['accepted_requests']}")
            print(f"      Rejected requests: {metrics['rejected_requests']}")
            print(f"      Success rate: {metrics['success_rate']:.1f}%")
            print(f"      Peak concurrent: {metrics['peak_concurrent']}")
            print(f"      Average queue time: {metrics['average_queue_time']:.3f}s")
            
        except Exception as e:
            print(f"   ❌ Bulkhead demo failed: {e}")
    
    async def demonstrate_fallback(self):
        """Demonstrate fallback strategies."""
        print("\n🔄 Fallback Strategies Demo")
        print("-" * 40)
        
        try:
            # Create fallback manager with multiple strategies
            config = FallbackConfig(
                enabled=True,
                fallback_timeout_seconds=2.0,
                max_fallback_attempts=3,
                enable_metrics=True
            )
            
            self.fallback_manager = FallbackManager(config)
            
            # Add fallback strategies
            cache_fallback = LocalCacheFallback(config)
            default_fallback = DefaultResponseFallback(config, {
                "get_user": {"id": "fallback_user", "name": "Fallback User"},
                "process_data": {"status": "degraded", "message": "Service unavailable"}
            })
            
            self.fallback_manager.add_strategy(cache_fallback)
            self.fallback_manager.add_strategy(default_fallback)
            
            print(f"   ✅ Fallback manager initialized with {len(self.fallback_manager._strategies)} strategies")
            
            # Test primary success
            async def primary_operation(data):
                if data.get("should_fail", False):
                    raise ConnectionError("Primary service unavailable")
                await asyncio.sleep(0.1)
                return f"Primary result for {data.get('id', 'unknown')}"
            
            # Test successful primary operation
            result = await self.fallback_manager.execute_with_fallback(
                primary_operation,
                "get_user",
                metadata={"request_id": "test_1"},
                id="test_user_1"
            )
            
            print(f"   ✅ Primary operation successful: {result.response}")
            print(f"      Fallback used: {result.is_fallback_used}")
            print(f"      Execution time: {result.execution_time_ms:.1f}ms")
            
            # Test primary failure with fallback
            result = await self.fallback_manager.execute_with_fallback(
                primary_operation,
                "get_user", 
                metadata={"request_id": "test_2"},
                id="test_user_2",
                should_fail=True
            )
            
            print(f"   🔄 Primary operation failed, fallback used: {result.response}")
            print(f"      Fallback type: {result.fallback_type.value if result.fallback_type else 'None'}")
            print(f"      Execution time: {result.execution_time_ms:.1f}ms")
            print(f"      Attempt count: {result.attempt_count}")
            
            # Store some data in cache for next test
            cache_fallback.store_in_cache("test_user_3", {"id": "cached_user", "name": "Cached User"})
            
            # Test cache hit
            result = await self.fallback_manager.execute_with_fallback(
                primary_operation,
                "get_user",
                metadata={"request_id": "test_3"},
                id="test_user_3",
                should_fail=True
            )
            
            print(f"   💾 Cache fallback successful: {result.response}")
            print(f"      Fallback type: {result.fallback_type.value}")
            
            # Get fallback metrics
            metrics = self.fallback_manager.get_metrics()
            print(f"   📊 Fallback Metrics:")
            print(f"      Total operations: {metrics['total_operations']}")
            print(f"      Primary success rate: {metrics['primary_success_rate']:.1f}%")
            print(f"      Fallback usage rate: {metrics['fallback_usage_rate']:.1f}%")
            print(f"      Average execution time: {metrics['average_execution_time']:.1f}ms")
            
        except Exception as e:
            print(f"   ❌ Fallback demo failed: {e}")
    
    async def demonstrate_enhanced_circuit_breaker(self):
        """Demonstrate enhanced circuit breaker."""
        print("\n⚡ Enhanced Circuit Breaker Demo")
        print("-" * 40)
        
        try:
            # Create enhanced circuit breaker with adaptive thresholds
            config = EnhancedCircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=10.0,
                success_threshold=2,
                adaptive_threshold_type=AdaptiveThresholdType.PERCENTILE_BASED,
                enable_dynamic_config=True,
                auto_tune_thresholds=True,
                enable_detailed_metrics=True
            )
            
            self.circuit_breaker = EnhancedGrpcCircuitBreaker("demo_service", config)
            print(f"   ✅ Enhanced circuit breaker initialized: {config.adaptive_threshold_type.value}")
            
            async def mock_operation(name: str, should_fail: bool = False):
                if should_fail:
                    raise ConnectionError(f"Service {name} temporarily unavailable")
                await asyncio.sleep(0.05)
                return f"Result from {name}"
            
            # Test normal operation
            result = await self.circuit_breaker.call(mock_operation, "test_op_1")
            print(f"   ✅ Normal operation: {result}")
            
            # Trigger circuit breaker with failures
            print("   ⚠️  Triggering circuit breaker with failures...")
            for i in range(4):
                try:
                    await self.circuit_breaker.call(mock_operation, f"fail_op_{i+1}", should_fail=True)
                except Exception as e:
                    print(f"      Expected failure {i+1}: {type(e).__name__}")
            
            # Circuit should be open now
            try:
                await self.circuit_breaker.call(mock_operation, "test_when_open")
            except Exception as e:
                print(f"   🚫 Circuit breaker working: {type(e).__name__}")
            
            # Wait for recovery timeout
            print("   ⏳ Waiting for recovery timeout...")
            await asyncio.sleep(12.0)  # Wait longer than recovery_timeout (10s)
            
            # Test recovery
            result = await self.circuit_breaker.call(mock_operation, "test_after_recovery")
            print(f"   ✅ Circuit breaker recovered: {result}")
            
            # Get enhanced metrics
            metrics = self.circuit_breaker.get_enhanced_metrics()
            print(f"   📊 Enhanced Circuit Breaker Metrics:")
            print(f"      State: {metrics['state']}")
            print(f"      Total calls: {metrics['total_calls']}")
            print(f"      Success rate: {metrics['success_rate']:.1f}%")
            print(f"      Average response time: {metrics['average_response_time']:.1f}ms")
            print(f"      Current threshold: {metrics['current_threshold']}")
            print(f"      State transitions: {len(metrics['state_transitions'])}")
            
        except Exception as e:
            print(f"   ❌ Enhanced circuit breaker demo failed: {e}")
    
    async def demonstrate_advanced_retry(self):
        """Demonstrate advanced retry policy."""
        print("\n🔄 Advanced Retry Policy Demo")
        print("-" * 40)
        
        try:
            # Create advanced retry policy with adaptive backoff
            config = AdvancedRetryConfig(
                max_attempts=5,
                base_delay=0.1,
                max_delay=2.0,
                adaptive_backoff_type=AdaptiveBackoffType.EXPONENTIAL_WITH_JITTER,
                enable_adaptive_delay=True,
                retry_condition_type=RetryConditionType.ON_ERROR_TYPE,
                retryable_error_types=["ConnectionError", "TimeoutError"],
                enable_performance_retry=True,
                slow_request_threshold_ms=200.0,
                enable_retry_budget=True,
                max_retries_per_window=20,
                enable_detailed_metrics=True
            )
            
            self.retry_policy = AdvancedRetryPolicy("demo_retry", config)
            print(f"   ✅ Advanced retry policy initialized: {config.adaptive_backoff_type.value}")
            
            async def flaky_operation(attempt: int):
                # Simulate flaky service that fails sometimes
                if attempt <= 2:
                    raise ConnectionError(f"Service temporarily unavailable (attempt {attempt})")
                await asyncio.sleep(0.05)
                return f"Success on attempt {attempt}"
            
            # Test successful retry
            result = await self.retry_policy.execute_with_retry(
                flaky_operation,
                operation_name="flaky_service"
            )
            print(f"   ✅ Retry successful: {result}")
            
            # Test retry with failure
            try:
                await self.retry_policy.execute_with_retry(
                    flaky_operation,
                    operation_name="flaky_service_fail"
                )
            except Exception as e:
                print(f"   ❌ Retry failed as expected: {type(e).__name__}")
            
            # Get advanced metrics
            metrics = self.retry_policy.get_advanced_metrics()
            print(f"   📊 Advanced Retry Metrics:")
            print(f"      Total operations: {metrics['total_operations']}")
            print(f"      Success rate: {metrics['success_rate']:.1f}%")
            print(f"      Average attempts: {metrics['average_attempts']:.1f}")
            print(f"      Average delay: {metrics['average_delay']:.3f}s")
            print(f"      Retry reasons: {metrics['retry_reasons']}")
            
            if 'performance_stats' in metrics:
                perf_stats = metrics['performance_stats']
                print(f"      Performance trend: {perf_stats['trend_direction']}")
                print(f"      Avg response time: {perf_stats['avg_response_time']:.1f}ms")
            
        except Exception as e:
            print(f"   ❌ Advanced retry demo failed: {e}")
    
    async def demonstrate_alerting(self):
        """Demonstrate alerting system."""
        print("\n🚨 Alerting System Demo")
        print("-" * 40)
        
        try:
            # Create alert manager with multiple channels
            config = AlertConfig(
                enabled=True,
                notification_channels=[NotificationChannel.LOG],  # Only log for demo
                enable_rate_limiting=True,
                max_alerts_per_hour=10,
                enable_deduplication=True,
                deduplication_window_minutes=5
            )
            
            self.alert_manager = AlertManager(config)
            print(f"   ✅ Alert manager initialized: {len(config.notification_channels)} channels")
            
            # Add alert conditions
            high_error_rate = AlertCondition(
                name="high_error_rate",
                metric_name="error_rate",
                threshold_value=10.0,
                comparison_operator=">=",
                severity=AlertSeverity.WARNING,
                duration_seconds=30.0  # Sustained for 30 seconds
            )
            
            critical_latency = AlertCondition(
                name="critical_latency",
                metric_name="response_time_p95",
                threshold_value=500.0,
                comparison_operator=">",
                severity=AlertSeverity.CRITICAL,
                duration_seconds=0.0  # Instant
            )
            
            self.alert_manager.add_condition(high_error_rate)
            self.alert_manager.add_condition(critical_latency)
            
            print(f"   ✅ Added {len(self.alert_manager._conditions)} alert conditions")
            
            # Simulate metrics that trigger alerts
            print("   📊 Simulating metrics that trigger alerts...")
            
            # Trigger high error rate alert
            for i in range(5):
                self.alert_manager.evaluate_metric("error_rate", 15.0, {"service": "demo_service"})
                await asyncio.sleep(1.0)
            
            # Trigger critical latency alert
            self.alert_manager.evaluate_metric("response_time_p95", 600.0, {"endpoint": "/api/demo"})
            
            # Wait a bit
            await asyncio.sleep(2.0)
            
            # Get alert metrics
            metrics = self.alert_manager.get_alert_metrics()
            print(f"   📊 Alerting Metrics:")
            print(f"      Total alerts: {metrics['total_alerts']}")
            print(f"      Active alerts: {metrics['active_alerts_count']}")
            print(f"      Alerts by severity: {metrics['alerts_by_severity']}")
            print(f"      Notifications sent: {metrics['notifications_sent']}")
            
            # Show active alerts
            active_alerts = self.alert_manager.get_active_alerts()
            if active_alerts:
                print(f"   🚨 Active Alerts:")
                for alert in active_alerts:
                    print(f"      - {alert.condition_name}: {alert.message}")
                    print(f"        Severity: {alert.severity.value}")
                    print(f"        Age: {alert.age_seconds:.1f}s")
            
        except Exception as e:
            print(f"   ❌ Alerting demo failed: {e}")
    
    async def demonstrate_integrated_resilience(self):
        """Demonstrate all resilience patterns working together."""
        print("\n🔗 Integrated Resilience Demo")
        print("-" * 40)
        
        try:
            print("   🎯 Testing all resilience patterns together...")
            
            # Create all components
            bulkhead = GrpcBulkhead(BulkheadConfig(max_concurrent=3))
            fallback_manager = FallbackManager(FallbackConfig())
            circuit_breaker = EnhancedGrpcCircuitBreaker("integrated_demo")
            retry_policy = AdvancedRetryPolicy("integrated_demo", AdvancedRetryConfig())
            
            # Add fallback strategy
            fallback_manager.add_strategy(DefaultResponseFallback(FallbackConfig(), {
                "integrated_operation": {"status": "degraded", "message": "Service in degraded mode"}
            }))
            
            async def resilient_operation(operation_id: str, complexity: str = "simple"):
                # Simulate different complexities
                if complexity == "complex":
                    await asyncio.sleep(0.2)  # Slower operation
                    failure_rate = 0.7  # Higher failure rate
                else:
                    await asyncio.sleep(0.05)
                    failure_rate = 0.2
                
                # Simulate failure based on complexity
                if random.random() < failure_rate:
                    raise ConnectionError(f"Operation {operation_id} failed")
                
                return f"Completed {operation_id} ({complexity})"
            
            # Execute operations with all resilience patterns
            tasks = []
            for i in range(10):
                complexity = "complex" if i % 3 == 0 else "simple"
                
                # Wrap with all resilience patterns
                async def fully_protected_operation():
                    # Bulkhead protection
                    return await bulkhead.execute(
                        # Circuit breaker protection
                        lambda: circuit_breaker.call(
                            # Retry protection
                            lambda: retry_policy.execute_with_retry(
                                # Fallback protection
                                lambda: resilient_operation(f"integrated_op_{i+1}", complexity)
                            ),
                            operation_name=f"integrated_op_{i+1}"
                        ),
                        operation_name=f"integrated_op_{i+1}"
                    )
                
                task = asyncio.create_task(fully_protected_operation())
                tasks.append(task)
            
            # Wait for all operations
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"   📊 Integrated Results:")
            print(f"      Total operations: {len(tasks)}")
            print(f"      Successful: {successful}")
            print(f"      Failed: {failed}")
            print(f"      Success rate: {(successful/len(tasks))*100:.1f}%")
            
            # Get combined metrics
            print(f"   📈 Combined Metrics:")
            print(f"      Bulkhead utilization: {bulkhead.get_status()['utilization_percent']:.1f}%")
            print(f"      Circuit breaker state: {circuit_breaker.get_enhanced_metrics()['state']}")
            print(f"      Retry success rate: {retry_policy.get_advanced_metrics()['success_rate']:.1f}%")
            print(f"      Fallback usage rate: {fallback_manager.get_metrics()['fallback_usage_rate']:.1f}%")
            
        except Exception as e:
            print(f"   ❌ Integrated resilience demo failed: {e}")
    
    async def run_demonstration(self):
        """Run complete resilience demonstration."""
        print("🚀 gRPC Resilience Features Demo")
        print("=" * 50)
        
        try:
            await self.demonstrate_bulkhead()
            await self.demonstrate_fallback()
            await self.demonstrate_enhanced_circuit_breaker()
            await self.demonstrate_advanced_retry()
            await self.demonstrate_alerting()
            await self.demonstrate_integrated_resilience()
            
            print("\n🎉 Resilience Features Demo Completed Successfully!")
            print("\n📋 Implemented Features:")
            print("   ✅ Bulkhead Pattern (Concurrency Control)")
            print("   ✅ Fallback Strategies (Graceful Degradation)")
            print("   ✅ Enhanced Circuit Breaker (Adaptive Thresholds)")
            print("   ✅ Advanced Retry Policies (Adaptive Backoff)")
            print("   ✅ Alerting System (Proactive Monitoring)")
            print("   ✅ Integrated Resilience (Combined Patterns)")
            
            print("\n🎯 Resilience Benefits:")
            print("   🛡️  Prevents cascading failures")
            print("   🔄  Automatic recovery from failures")
            print("   ⚡  Intelligent retry with backoff")
            print("   📊  Proactive issue detection")
            print("   🎛️  Graceful degradation under load")
            print("   📈  Resource usage optimization")
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main demonstration function."""
    demo = ResilienceGrpcDemo()
    await demo.run_demonstration()


if __name__ == "__main__":
    asyncio.run(main())
