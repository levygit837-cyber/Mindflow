"""Enhanced gRPC server component initialization.

Provides component setup for resilience, performance,
and monitoring features.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.grpc_internal.monitoring.alerting import (
    AlertCondition,
    AlertConfig,
    AlertManager,
    AlertSeverity,
)
from mindflow_backend.grpc_internal.monitoring.metrics import GrpcMetricsCollector
from mindflow_backend.grpc_internal.monitoring.prometheus import PrometheusExporter
from mindflow_backend.grpc_internal.performance.caching.cache import CacheConfig, GrpcResponseCache
from mindflow_backend.grpc_internal.performance.compression.compressor import (
    CompressionAlgorithm,
    CompressionConfig,
    GrpcMessageCompressor,
)
from mindflow_backend.grpc_internal.performance.monitoring.profiler import (
    GrpcProfiler,
    ProfileConfig,
    ProfileLevel,
)
from mindflow_backend.grpc_internal.performance.optimization.optimizer import (
    GrpcOptimizer,
    OptimizationConfig,
)
from mindflow_backend.grpc_internal.performance.pooling.manager import (
    GrpcConnectionPoolManager,
    PoolManagerConfig,
)
from mindflow_backend.grpc_internal.resilience.advanced_retry import (
    AdaptiveBackoffType,
    AdvancedRetryConfig,
    AdvancedRetryPolicy,
    RetryConditionType,
)
from mindflow_backend.grpc_internal.resilience.bulkhead import BulkheadConfig, GrpcBulkhead
from mindflow_backend.grpc_internal.resilience.enhanced_circuit_breaker import (
    AdaptiveThresholdType,
    EnhancedCircuitBreakerConfig,
    EnhancedGrpcCircuitBreaker,
)
from mindflow_backend.grpc_internal.resilience.fallback import (
    DefaultResponseFallback,
    FallbackConfig,
    FallbackManager,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def initialize_monitoring_components(
    config: Any,
    metrics_collector: GrpcMetricsCollector | None,
) -> tuple[PrometheusExporter | None, AlertManager | None]:
    """Initialize monitoring and alerting components.

    Args:
        config: gRPC configuration
        metrics_collector: Metrics collector instance

    Returns:
        Tuple of (prometheus_exporter, alert_manager)
    """
    prometheus_exporter = None
    alert_manager = None

    # Initialize Prometheus exporter
    if config.enable_metrics and config.grpc_prometheus_port:
        prometheus_exporter = PrometheusExporter(
            metrics_collector,
            host="0.0.0.0",
            port=config.grpc_prometheus_port,
        )

    # Initialize alerting system
    if config.enable_metrics:
        alert_config = AlertConfig(
            enabled=True,
            notification_channels=[],
            enable_rate_limiting=True,
            max_alerts_per_hour=50,
        )
        alert_manager = AlertManager(alert_config)

        # Add default alert conditions
        high_error_rate = AlertCondition(
            name="high_error_rate",
            metric_name="error_rate",
            threshold_value=10.0,
            comparison_operator=">=",
            severity=AlertSeverity.WARNING,
            duration_seconds=60.0,
        )
        high_latency = AlertCondition(
            name="high_latency",
            metric_name="response_time_p95",
            threshold_value=500.0,
            comparison_operator=">",
            severity=AlertSeverity.ERROR,
            duration_seconds=30.0,
        )

        alert_manager.add_condition(high_error_rate)
        alert_manager.add_condition(high_latency)

    return prometheus_exporter, alert_manager


def initialize_resilience_components(config: Any) -> dict[str, Any]:
    """Initialize resilience components.

    Args:
        config: gRPC configuration

    Returns:
        Dictionary with resilience components
    """
    components: dict[str, Any] = {
        "circuit_breaker": None,
        "retry_policy": None,
        "bulkhead": None,
        "fallback_manager": None,
    }

    if not getattr(config, "enable_resilience", True):
        return components

    # Enhanced circuit breaker
    circuit_config = EnhancedCircuitBreakerConfig(
        failure_threshold=getattr(config, "circuit_breaker_failure_threshold", 5),
        recovery_timeout=getattr(config, "circuit_breaker_recovery_timeout", 60.0),
        success_threshold=getattr(config, "circuit_breaker_success_threshold", 3),
        adaptive_threshold_type=AdaptiveThresholdType.PERCENTILE_BASED,
        enable_dynamic_config=True,
        auto_tune_thresholds=True,
    )
    components["circuit_breaker"] = EnhancedGrpcCircuitBreaker(
        "grpc_server",
        circuit_config,
    )

    # Advanced retry policy
    retry_config = AdvancedRetryConfig(
        max_attempts=getattr(config, "max_attempts", 3),
        base_delay=getattr(config, "initial_retry_delay_ms", 100) / 1000.0,
        max_delay=getattr(config, "max_retry_delay_ms", 1000) / 1000.0,
        adaptive_backoff_type=AdaptiveBackoffType.EXPONENTIAL_WITH_JITTER,
        enable_adaptive_delay=True,
        retry_condition_type=RetryConditionType.ON_ERROR_TYPE,
        enable_performance_retry=True,
    )
    components["retry_policy"] = AdvancedRetryPolicy("grpc_server", retry_config)

    # Bulkhead pattern
    bulkhead_config = BulkheadConfig(
        max_concurrent=getattr(config, "bulkhead_max_concurrent", 100),
        max_queue_size=getattr(config, "bulkhead_max_queue_size", 1000),
        queue_timeout_seconds=getattr(config, "bulkhead_queue_timeout", 30.0),
        execution_timeout_seconds=getattr(config, "default_timeout_seconds", 300),
        enable_metrics=True,
    )
    components["bulkhead"] = GrpcBulkhead(bulkhead_config)

    # Fallback manager
    fallback_config = FallbackConfig(
        enabled=True,
        fallback_timeout_seconds=5.0,
        max_fallback_attempts=3,
        enable_metrics=True,
    )
    components["fallback_manager"] = FallbackManager(fallback_config)

    # Add default fallback strategies
    default_responses = {
        "agent_chat": {
            "status": "degraded",
            "message": "AI service temporarily unavailable",
        },
        "stream_chat": {
            "status": "degraded",
            "message": "Stream service temporarily unavailable",
        },
    }
    default_fallback = DefaultResponseFallback(fallback_config, default_responses)
    components["fallback_manager"].add_strategy(default_fallback)

    return components


def initialize_performance_components(config: Any) -> dict[str, Any]:
    """Initialize performance optimization components.

    Args:
        config: gRPC configuration

    Returns:
        Dictionary with performance components
    """
    components: dict[str, Any] = {
        "connection_pool_manager": None,
        "message_compressor": None,
        "response_cache": None,
        "profiler": None,
        "optimizer": None,
    }

    if not getattr(config, "enable_performance_optimization", True):
        return components

    # Connection pool manager
    components["connection_pool_manager"] = GrpcConnectionPoolManager(
        PoolManagerConfig(),
    )

    # Message compressor
    compression_config = CompressionConfig(
        algorithm=getattr(
            config,
            "compression_algorithm",
            CompressionAlgorithm.GZIP,
        ),
        compression_level=getattr(config, "compression_level", 6),
        threshold_bytes=getattr(config, "compression_threshold", 512),
        enable_compression_stats=True,
    )
    components["message_compressor"] = GrpcMessageCompressor(compression_config)

    # Response cache
    cache_config = CacheConfig(
        max_size=getattr(config, "cache_max_size", 1000),
        max_memory_mb=getattr(config, "cache_max_memory_mb", 100),
        default_ttl_seconds=getattr(config, "cache_default_ttl", 300),
        enable_stats=True,
    )
    components["response_cache"] = GrpcResponseCache(cache_config)

    # Performance profiler
    profiler_config = ProfileConfig(
        enabled=getattr(config, "enable_profiling", True),
        level=ProfileLevel.BASIC,
        sampling_rate=getattr(config, "profiling_sampling_rate", 0.1),
        max_profiles=getattr(config, "profiling_max_profiles", 10000),
    )
    components["profiler"] = GrpcProfiler(profiler_config)

    # Performance optimizer
    optimization_config = OptimizationConfig(
        enabled=getattr(config, "enable_optimization", True),
        auto_tune=getattr(config, "enable_auto_tuning", False),
        optimization_interval_seconds=getattr(config, "optimization_interval", 300),
        min_data_points=getattr(config, "optimization_min_data_points", 100),
    )
    components["optimizer"] = GrpcOptimizer(optimization_config)

    return components