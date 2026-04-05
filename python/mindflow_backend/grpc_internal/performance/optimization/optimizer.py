"""Automatic gRPC performance optimizer.

Provides intelligent optimization of gRPC settings based on
historical performance data and system characteristics.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from mindflow_backend.grpc_internal.config.config import GrpcConfig
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class OptimizationType(Enum):
    """Types of optimizations."""
    CONNECTION_TUNING = "connection_tuning"
    TIMEOUT_TUNING = "timeout_tuning"
    RETRY_TUNING = "retry_tuning"
    BUFFER_TUNING = "buffer_tuning"
    CIRCUIT_BREAKER_TUNING = "circuit_breaker_tuning"
    COMPRESSION_TUNING = "compression_tuning"
    CACHING_TUNING = "caching_tuning"


@dataclass
class OptimizationConfig:
    """Configuration for performance optimizer."""
    
    # Optimization settings
    enabled: bool = True
    auto_apply: bool = False  # Auto-apply optimizations
    require_confirmation: bool = True
    
    # Data requirements
    min_data_points: int = 100
    analysis_window_seconds: int = 3600  # 1 hour
    
    # Optimization thresholds
    min_improvement_percent: float = 5.0  # Minimum improvement to apply
    max_risk_level: float = 0.3  # Maximum risk level for auto-apply
    
    # Performance targets
    target_latency_ms: float = 50.0
    target_throughput_rps: float = 1000.0
    target_error_rate_percent: float = 1.0
    
    # Safety constraints
    max_connections: int = 10000
    max_timeout_seconds: int = 300
    max_memory_mb: int = 1024
    max_cpu_percent: float = 80.0
    
    # Optimization frequency
    optimization_interval_seconds: int = 300  # 5 minutes
    max_optimizations_per_hour: int = 12
    
    # Monitoring
    enable_optimization_tracking: bool = True
    rollback_on_regression: bool = True
    regression_threshold_percent: float = 10.0


@dataclass
class OptimizationResult:
    """Result of optimization analysis."""
    
    optimization_type: OptimizationType
    current_config: dict[str, Any]
    recommended_config: dict[str, Any]
    expected_improvement_percent: float
    confidence_score: float  # 0-100
    risk_level: float  # 0-1
    reasoning: str
    data_points: int
    analysis_timestamp: float
    
    # Applied information
    applied: bool = False
    applied_timestamp: float | None = None
    rollback_timestamp: float | None = None
    actual_improvement_percent: float | None = None
    
    @property
    def is_safe_to_apply(self) -> bool:
        """Check if optimization is safe to apply."""
        return (self.confidence_score >= 70 and 
                self.risk_level <= 0.3 and
                self.expected_improvement_percent >= 5.0)


class GrpcOptimizer:
    """gRPC performance optimizer with intelligent tuning."""
    
    def __init__(self, config: OptimizationConfig | None = None):
        self.config = config or OptimizationConfig()
        self._optimization_history: list[OptimizationResult] = []
        self._last_optimization_time = 0.0
        self._optimization_count = 0
        
        _logger.info(
            "grpc_optimizer_initialized",
            enabled=self.config.enabled,
            auto_apply=self.config.auto_apply
        )
    
    def analyze_performance(self, current_config: GrpcConfig, 
                          performance_data: list[dict[str, Any]]) -> list[OptimizationResult]:
        """Analyze performance data and generate optimization recommendations."""
        if not self.config.enabled:
            return []
        
        if len(performance_data) < self.config.min_data_points:
            _logger.warning(
                "insufficient_data_for_optimization",
                data_points=len(performance_data),
                required=self.config.min_data_points
            )
            return []
        
        optimizations = []
        
        # Analyze different optimization types
        optimizations.extend(self._analyze_connection_tuning(current_config, performance_data))
        optimizations.extend(self._analyze_timeout_tuning(current_config, performance_data))
        optimizations.extend(self._analyze_retry_tuning(current_config, performance_data))
        optimizations.extend(self._analyze_buffer_tuning(current_config, performance_data))
        optimizations.extend(self._analyze_circuit_breaker_tuning(current_config, performance_data))
        
        # Sort by expected improvement
        optimizations.sort(key=lambda x: x.expected_improvement_percent, reverse=True)
        
        return optimizations
    
    def apply_optimization(self, optimization: OptimizationResult, 
                         current_config: GrpcConfig) -> GrpcConfig:
        """Apply optimization to configuration."""
        if not optimization.is_safe_to_apply and self.config.require_confirmation:
            raise ValueError("Optimization not safe to apply without confirmation")
        
        # Create new config with applied optimization
        new_config_dict = current_config.dict()
        new_config_dict.update(optimization.recommended_config)
        
        new_config = GrpcConfig(**new_config_dict)
        
        # Update optimization tracking
        optimization.applied = True
        optimization.applied_timestamp = time.time()
        self._optimization_history.append(optimization)
        self._optimization_count += 1
        self._last_optimization_time = time.time()
        
        _logger.info(
            "optimization_applied",
            type=optimization.optimization_type.value,
            improvement_percent=optimization.expected_improvement_percent,
            confidence=optimization.confidence_score
        )
        
        return new_config
    
    def rollback_optimization(self, optimization: OptimizationResult,
                            current_config: GrpcConfig) -> GrpcConfig:
        """Rollback an applied optimization."""
        if not optimization.applied:
            raise ValueError("Optimization was not applied")
        
        # Restore original config
        rollback_config_dict = current_config.dict()
        rollback_config_dict.update(optimization.current_config)
        
        rollback_config = GrpcConfig(**rollback_config_dict)
        
        # Update optimization tracking
        optimization.rollback_timestamp = time.time()
        
        _logger.info(
            "optimization_rolled_back",
            type=optimization.optimization_type.value,
            applied_duration=time.time() - optimization.applied_timestamp
        )
        
        return rollback_config
    
    def get_optimization_history(self, limit: int = 50) -> list[OptimizationResult]:
        """Get optimization history."""
        return self._optimization_history[-limit:]
    
    def get_optimization_stats(self) -> dict[str, Any]:
        """Get optimization statistics."""
        if not self._optimization_history:
            return {
                'total_optimizations': 0,
                'applied_optimizations': 0,
                'rolled_back_optimizations': 0,
                'average_improvement': 0.0,
            }
        
        applied = [o for o in self._optimization_history if o.applied]
        rolled_back = [o for o in applied if o.rollback_timestamp is not None]
        
        actual_improvements = [o.actual_improvement_percent for o in applied 
                             if o.actual_improvement_percent is not None]
        
        return {
            'total_optimizations': len(self._optimization_history),
            'applied_optimizations': len(applied),
            'rolled_back_optimizations': len(rolled_back),
            'average_improvement': statistics.mean(actual_improvements) if actual_improvements else 0.0,
            'optimization_rate': self._optimization_count / max(1, time.time() - self._last_optimization_time) * 3600,
        }
    
    def _analyze_connection_tuning(self, config: GrpcConfig, 
                                 data: list[dict[str, Any]]) -> list[OptimizationResult]:
        """Analyze connection pool tuning."""
        optimizations = []
        
        # Analyze connection utilization
        if 'connection_utilization' in data[0]:
            utilizations = [d['connection_utilization'] for d in data]
            avg_utilization = statistics.mean(utilizations)
            max_utilization = max(utilizations)
            
            # If connections are underutilized, reduce pool size
            if avg_utilization < 0.5 and config.max_connections > 50:
                recommended_connections = max(10, int(config.max_connections * 0.7))
                
                optimizations.append(OptimizationResult(
                    optimization_type=OptimizationType.CONNECTION_TUNING,
                    current_config={'max_connections': config.max_connections},
                    recommended_config={'max_connections': recommended_connections},
                    expected_improvement_percent=5.0,
                    confidence_score=80.0,
                    risk_level=0.1,
                    reasoning=f"Connection utilization is {avg_utilization:.1%}, reducing pool size saves resources",
                    data_points=len(data),
                    analysis_timestamp=time.time()
                ))
            
            # If connections are overutilized, increase pool size
            elif max_utilization > 0.9 and config.max_connections < self.config.max_connections:
                recommended_connections = min(self.config.max_connections, int(config.max_connections * 1.5))
                
                optimizations.append(OptimizationResult(
                    optimization_type=OptimizationType.CONNECTION_TUNING,
                    current_config={'max_connections': config.max_connections},
                    recommended_config={'max_connections': recommended_connections},
                    expected_improvement_percent=15.0,
                    confidence_score=85.0,
                    risk_level=0.2,
                    reasoning=f"Connection utilization reaches {max_utilization:.1%}, increasing pool size improves throughput",
                    data_points=len(data),
                    analysis_timestamp=time.time()
                ))
        
        return optimizations
    
    def _analyze_timeout_tuning(self, config: GrpcConfig,
                               data: list[dict[str, Any]]) -> list[OptimizationResult]:
        """Analyze timeout settings."""
        optimizations = []
        
        # Analyze request duration distribution
        if 'duration_ms' in data[0]:
            durations = [d['duration_ms'] for d in data]
            p95_duration = statistics.quantiles(durations, n=100)[94]  # P95
            avg_duration = statistics.mean(durations)
            
            # If timeouts are much longer than P95, reduce them
            if config.default_timeout_seconds * 1000 > p95_duration * 3:
                recommended_timeout = max(30, int(p95_duration * 2))  # 2x P95, minimum 30s
                
                optimizations.append(OptimizationResult(
                    optimization_type=OptimizationType.TIMEOUT_TUNING,
                    current_config={'default_timeout_seconds': config.default_timeout_seconds},
                    recommended_config={'default_timeout_seconds': recommended_timeout},
                    expected_improvement_percent=8.0,
                    confidence_score=75.0,
                    risk_level=0.15,
                    reasoning=f"Current timeout ({config.default_timeout_seconds}s) is much longer than P95 ({p95_duration:.0f}ms), reducing improves responsiveness",
                    data_points=len(data),
                    analysis_timestamp=time.time()
                ))
            
            # If many requests are timing out, increase timeout
            timeout_rate = len([d for d in data if d.get('timed_out', False)]) / len(data)
            if timeout_rate > 0.05 and config.default_timeout_seconds < self.config.max_timeout_seconds:
                recommended_timeout = min(self.config.max_timeout_seconds, int(config.default_timeout_seconds * 1.5))
                
                optimizations.append(OptimizationResult(
                    optimization_type=OptimizationType.TIMEOUT_TUNING,
                    current_config={'default_timeout_seconds': config.default_timeout_seconds},
                    recommended_config={'default_timeout_seconds': recommended_timeout},
                    expected_improvement_percent=20.0,
                    confidence_score=90.0,
                    risk_level=0.1,
                    reasoning=f"Timeout rate is {timeout_rate:.1%}, increasing timeout reduces failures",
                    data_points=len(data),
                    analysis_timestamp=time.time()
                ))
        
        return optimizations
    
    def _analyze_retry_tuning(self, config: GrpcConfig,
                             data: list[dict[str, Any]]) -> list[OptimizationResult]:
        """Analyze retry policy tuning."""
        optimizations = []
        
        # Analyze retry success rates
        if 'retry_attempts' in data[0]:
            retry_data = [d for d in data if d.get('retry_attempts', 0) > 0]
            
            if retry_data:
                retry_success_rate = len([d for d in retry_data if d.get('success', False)]) / len(retry_data)
                
                # If retry success rate is low, reduce max attempts
                if retry_success_rate < 0.3 and config.max_attempts > 2:
                    recommended_attempts = max(1, config.max_attempts - 1)
                    
                    optimizations.append(OptimizationResult(
                        optimization_type=OptimizationType.RETRY_TUNING,
                        current_config={'max_attempts': config.max_attempts},
                        recommended_config={'max_attempts': recommended_attempts},
                        expected_improvement_percent=10.0,
                        confidence_score=70.0,
                        risk_level=0.1,
                        reasoning=f"Retry success rate is {retry_success_rate:.1%}, reducing attempts saves resources",
                        data_points=len(retry_data),
                        analysis_timestamp=time.time()
                    ))
                
                # If retry success rate is high and failures are common, increase attempts
                failure_rate = len([d for d in data if not d.get('success', True)]) / len(data)
                if retry_success_rate > 0.7 and failure_rate > 0.1 and config.max_attempts < 5:
                    recommended_attempts = min(5, config.max_attempts + 1)
                    
                    optimizations.append(OptimizationResult(
                        optimization_type=OptimizationType.RETRY_TUNING,
                        current_config={'max_attempts': config.max_attempts},
                        recommended_config={'max_attempts': recommended_attempts},
                        expected_improvement_percent=15.0,
                        confidence_score=80.0,
                        risk_level=0.2,
                        reasoning=f"Retry success rate is {retry_success_rate:.1%} and failure rate is {failure_rate:.1%}, increasing attempts improves reliability",
                        data_points=len(retry_data),
                        analysis_timestamp=time.time()
                    ))
        
        return optimizations
    
    def _analyze_buffer_tuning(self, config: GrpcConfig,
                             data: list[dict[str, Any]]) -> list[OptimizationResult]:
        """Analyze buffer size tuning."""
        optimizations = []
        
        # Analyze message sizes
        if 'request_size_bytes' in data[0] and 'response_size_bytes' in data[0]:
            request_sizes = [d['request_size_bytes'] for d in data]
            response_sizes = [d['response_size_bytes'] for d in data]
            
            max_request = max(request_sizes)
            max_response = max(response_sizes)
            
            # If buffers are much larger than needed, reduce them
            current_max = max(config.max_receive_message_length, config.max_send_message_length)
            actual_max = max(max_request, max_response)
            
            if current_max > actual_max * 2:
                recommended_size = max(actual_max * 1.5, 1024 * 1024)  # 1.5x actual, minimum 1MB
                
                optimizations.append(OptimizationResult(
                    optimization_type=OptimizationType.BUFFER_TUNING,
                    current_config={
                        'max_receive_message_length': config.max_receive_message_length,
                        'max_send_message_length': config.max_send_message_length
                    },
                    recommended_config={
                        'max_receive_message_length': int(recommended_size),
                        'max_send_message_length': int(recommended_size)
                    },
                    expected_improvement_percent=5.0,
                    confidence_score=85.0,
                    risk_level=0.1,
                    reasoning=f"Buffer sizes ({current_max//(1024*1024)}MB) are much larger than needed ({actual_max//(1024*1024)}MB), reducing saves memory",
                    data_points=len(data),
                    analysis_timestamp=time.time()
                ))
            
            # If buffers are too small for some messages, increase them
            elif actual_max > current_max * 0.9:
                recommended_size = actual_max * 1.2
                
                optimizations.append(OptimizationResult(
                    optimization_type=OptimizationType.BUFFER_TUNING,
                    current_config={
                        'max_receive_message_length': config.max_receive_message_length,
                        'max_send_message_length': config.max_send_message_length
                    },
                    recommended_config={
                        'max_receive_message_length': int(recommended_size),
                        'max_send_message_length': int(recommended_size)
                    },
                    expected_improvement_percent=25.0,
                    confidence_score=95.0,
                    risk_level=0.2,
                    reasoning=f"Messages exceed buffer limits ({actual_max//(1024*1024)}MB > {current_max//(1024*1024)}MB), increasing prevents failures",
                    data_points=len(data),
                    analysis_timestamp=time.time()
                ))
        
        return optimizations
    
    def _analyze_circuit_breaker_tuning(self, config: GrpcConfig,
                                        data: list[dict[str, Any]]) -> list[OptimizationResult]:
        """Analyze circuit breaker tuning."""
        optimizations = []
        
        # Analyze failure patterns
        if 'circuit_breaker_state' in data[0]:
            failure_data = [d for d in data if d.get('success', False) == False]
            
            if failure_data:
                failure_rate = len(failure_data) / len(data)
                
                # If failure rate is high, lower circuit breaker threshold
                if failure_rate > 0.2 and config.circuit_breaker_threshold > 3:
                    recommended_threshold = max(3, config.circuit_breaker_threshold - 1)
                    
                    optimizations.append(OptimizationResult(
                        optimization_type=OptimizationType.CIRCUIT_BREAKER_TUNING,
                        current_config={'circuit_breaker_threshold': config.circuit_breaker_threshold},
                        recommended_config={'circuit_breaker_threshold': recommended_threshold},
                        expected_improvement_percent=12.0,
                        confidence_score=75.0,
                        risk_level=0.15,
                        reasoning=f"Failure rate is {failure_rate:.1%}, lowering threshold provides faster failure detection",
                        data_points=len(failure_data),
                        analysis_timestamp=time.time()
                    ))
                
                # If failure rate is low and circuit breaker is triggering often, increase threshold
                elif failure_rate < 0.05 and config.circuit_breaker_threshold < 10:
                    recommended_threshold = min(10, config.circuit_breaker_threshold + 2)
                    
                    optimizations.append(OptimizationResult(
                        optimization_type=OptimizationType.CIRCUIT_BREAKER_TUNING,
                        current_config={'circuit_breaker_threshold': config.circuit_breaker_threshold},
                        recommended_config={'circuit_breaker_threshold': recommended_threshold},
                        expected_improvement_percent=8.0,
                        confidence_score=70.0,
                        risk_level=0.1,
                        reasoning=f"Failure rate is low ({failure_rate:.1%}), increasing threshold reduces false positives",
                        data_points=len(failure_data),
                        analysis_timestamp=time.time()
                    ))
        
        return optimizations
