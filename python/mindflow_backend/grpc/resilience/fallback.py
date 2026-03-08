"""Fallback strategies for gRPC resilience.

Provides graceful degradation when primary services fail,
ensuring system continues to operate with reduced functionality.
"""

from __future__ import annotations

import asyncio
import time
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class FallbackType(Enum):
    """Types of fallback strategies."""
    LOCAL_CACHE = "local_cache"
    DEFAULT_RESPONSE = "default_response"
    ALTERNATIVE_SERVICE = "alternative_service"
    REDUCED_FUNCTIONALITY = "reduced_functionality"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class FallbackConfig:
    """Configuration for fallback strategies."""
    
    # Behavior settings
    enabled: bool = True
    fallback_timeout_seconds: float = 5.0
    max_fallback_attempts: int = 3
    
    # Cache settings
    cache_ttl_seconds: int = 300  # 5 minutes
    cache_size_limit: int = 1000
    
    # Retry settings
    retry_on_fallback_failure: bool = True
    fallback_retry_delay_seconds: float = 1.0
    
    # Metrics
    enable_metrics: bool = True
    track_fallback_reasons: bool = True


@dataclass
class FallbackResult:
    """Result of fallback execution."""
    
    success: bool
    fallback_used: bool
    fallback_type: Optional[FallbackType]
    response: Any
    error_message: Optional[str]
    execution_time_ms: float
    attempt_count: int
    
    @property
    def is_fallback_used(self) -> bool:
        """Check if fallback was used."""
        return self.fallback_used
    
    @property
    def is_primary_success(self) -> bool:
        """Check if primary operation succeeded."""
        return self.success and not self.fallback_used


class FallbackContext:
    """Context for fallback execution."""
    
    def __init__(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        self.operation_name = operation_name
        self.metadata = metadata or {}
        self.start_time = time.time()
        self.attempt_count = 0
        self.fallback_chain: List[FallbackType] = []


class FallbackStrategy(ABC):
    """Base class for fallback strategies."""
    
    def __init__(self, config: FallbackConfig):
        self.config = config
        self.metrics = {
            'total_executions': 0,
            'fallback_used': 0,
            'fallback_success': 0,
            'fallback_failure': 0,
            'primary_success': 0,
            'primary_failure': 0,
        }
    
    @abstractmethod
    async def execute_fallback(self, 
                           context: FallbackContext,
                           error: Exception,
                           **kwargs) -> Any:
        """Execute fallback logic."""
        pass
    
    @abstractmethod
    def get_fallback_type(self) -> FallbackType:
        """Get the type of this fallback strategy."""
        pass
    
    def update_metrics(self, 
                    primary_success: bool,
                    fallback_used: bool,
                    fallback_success: bool) -> None:
        """Update strategy metrics."""
        self.metrics['total_executions'] += 1
        
        if primary_success:
            self.metrics['primary_success'] += 1
        else:
            self.metrics['primary_failure'] += 1
        
        if fallback_used:
            self.metrics['fallback_used'] += 1
            if fallback_success:
                self.metrics['fallback_success'] += 1
            else:
                self.metrics['fallback_failure'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get strategy metrics."""
        total = self.metrics['total_executions']
        if total == 0:
            return self.metrics.copy()
        
        metrics = self.metrics.copy()
        metrics['fallback_usage_rate'] = (self.metrics['fallback_used'] / total) * 100
        metrics['fallback_success_rate'] = (
            (self.metrics['fallback_success'] / max(1, self.metrics['fallback_used'])) * 100
        )
        metrics['primary_success_rate'] = (self.metrics['primary_success'] / total) * 100
        
        return metrics


class LocalCacheFallback(FallbackStrategy):
    """Fallback using local cache."""
    
    def __init__(self, config: FallbackConfig, cache: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._cache = cache or {}
        self._cache_timestamps = {}
        self._cache_lock = threading.Lock()
    
    async def execute_fallback(self, 
                           context: FallbackContext,
                           error: Exception,
                           cache_key: Optional[str] = None,
                           **kwargs) -> Any:
        """Execute fallback using local cache."""
        if not cache_key:
            # Generate cache key from operation name and metadata
            cache_key = f"{context.operation_name}:{hash(str(context.metadata))}"
        
        with self._cache_lock:
            if cache_key in self._cache:
                # Check if cache entry is still valid
                cache_time = self._cache_timestamps.get(cache_key, 0)
                if time.time() - cache_time < self.config.cache_ttl_seconds:
                    _logger.info("fallback_cache_hit", key=cache_key)
                    return self._cache[cache_key]
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
                    del self._cache_timestamps[cache_key]
        
        _logger.warning("fallback_cache_miss", key=cache_key)
        raise ValueError(f"No cached value found for key: {cache_key}")
    
    def get_fallback_type(self) -> FallbackType:
        return FallbackType.LOCAL_CACHE
    
    def store_in_cache(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store value in cache."""
        with self._cache_lock:
            # Check size limit
            if len(self._cache) >= self.config.cache_size_limit:
                # Remove oldest entry (simplified LRU)
                oldest_key = next(iter(self._cache_timestamps))
                del self._cache[oldest_key]
                del self._cache_timestamps[oldest_key]
            
            self._cache[key] = value
            self._cache_timestamps[key] = time.time()
            
            if ttl_seconds:
                # Schedule expiration (simplified - would use actual scheduler)
                pass


class DefaultResponseFallback(FallbackStrategy):
    """Fallback using default responses."""
    
    def __init__(self, config: FallbackConfig, default_responses: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._default_responses = default_responses or {}
    
    async def execute_fallback(self, 
                           context: FallbackContext,
                           error: Exception,
                           **kwargs) -> Any:
        """Execute fallback using default response."""
        response_key = context.operation_name
        
        if response_key in self._default_responses:
            _logger.info("fallback_default_response", operation=response_key)
            return self._default_responses[response_key]
        
        # Generic default response
        _logger.warning("fallback_generic_response", operation=response_key)
        return {
            'status': 'degraded',
            'message': f'Service {response_key} is temporarily unavailable',
            'fallback_used': True,
            'timestamp': time.time()
        }
    
    def get_fallback_type(self) -> FallbackType:
        return FallbackType.DEFAULT_RESPONSE


class AlternativeServiceFallback(FallbackStrategy):
    """Fallback using alternative service endpoint."""
    
    def __init__(self, config: FallbackConfig, alternative_endpoints: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self._alternative_endpoints = alternative_endpoints or {}
    
    async def execute_fallback(self, 
                           context: FallbackContext,
                           error: Exception,
                           **kwargs) -> Any:
        """Execute fallback using alternative service."""
        operation_key = context.operation_name
        
        if operation_key in self._alternative_endpoints:
            endpoint = self._alternative_endpoints[operation_key]
            _logger.info("fallback_alternative_service", operation=operation_key, endpoint=endpoint)
            
            # In a real implementation, this would call the alternative service
            # For now, return a mock response
            return {
                'status': 'alternative',
                'message': f'Using alternative service for {operation_key}',
                'endpoint': endpoint,
                'fallback_used': True
            }
        
        raise ValueError(f"No alternative service configured for: {operation_key}")
    
    def get_fallback_type(self) -> FallbackType:
        return FallbackType.ALTERNATIVE_SERVICE


class ReducedFunctionalityFallback(FallbackStrategy):
    """Fallback with reduced functionality."""
    
    def __init__(self, config: FallbackConfig, reduced_handlers: Optional[Dict[str, Callable]] = None):
        super().__init__(config)
        self._reduced_handlers = reduced_handlers or {}
    
    async def execute_fallback(self, 
                           context: FallbackContext,
                           error: Exception,
                           **kwargs) -> Any:
        """Execute fallback with reduced functionality."""
        operation_key = context.operation_name
        
        if operation_key in self._reduced_handlers:
            handler = self._reduced_handlers[operation_key]
            _logger.info("fallback_reduced_functionality", operation=operation_key)
            
            try:
                return await handler(**kwargs)
            except Exception as handler_error:
                _logger.error("fallback_reduced_handler_failed", 
                             operation=operation_key, error=str(handler_error))
                raise
        
        # Generic reduced response
        return {
            'status': 'reduced',
            'message': f'Limited functionality for {operation_key}',
            'fallback_used': True
        }
    
    def get_fallback_type(self) -> FallbackType:
        return FallbackType.REDUCED_FUNCTIONALITY


class CircuitBreakerFallback(FallbackStrategy):
    """Fallback triggered by circuit breaker."""
    
    async def execute_fallback(self, 
                           context: FallbackContext,
                           error: Exception,
                           **kwargs) -> Any:
        """Execute circuit breaker fallback."""
        _logger.warning("fallback_circuit_breaker", 
                     operation=context.operation_name, error=str(error))
        
        return {
            'status': 'circuit_open',
            'message': f'Circuit breaker open for {context.operation_name}',
            'fallback_used': True,
            'error_type': type(error).__name__
        }
    
    def get_fallback_type(self) -> FallbackType:
        return FallbackType.CIRCUIT_BREAKER


class FallbackManager:
    """Manages multiple fallback strategies and execution."""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self._strategies: List[FallbackStrategy] = []
        self._metrics = {
            'total_operations': 0,
            'primary_success': 0,
            'fallback_used': 0,
            'fallback_success': 0,
            'average_execution_time': 0.0,
        }
        self._execution_times = []
        self._metrics_lock = threading.Lock()
    
    def add_strategy(self, strategy: FallbackStrategy) -> None:
        """Add a fallback strategy."""
        self._strategies.append(strategy)
        _logger.info("fallback_strategy_added", type=strategy.get_fallback_type().value)
    
    def remove_strategy(self, strategy_type: FallbackType) -> None:
        """Remove a fallback strategy by type."""
        self._strategies = [
            s for s in self._strategies 
            if s.get_fallback_type() != strategy_type
        ]
        _logger.info("fallback_strategy_removed", type=strategy_type.value)
    
    async def execute_with_fallback(self,
                                primary_func: Callable,
                                operation_name: str,
                                metadata: Optional[Dict[str, Any]] = None,
                                fallback_types: Optional[List[FallbackType]] = None,
                                **kwargs) -> FallbackResult:
        """Execute primary function with fallback support."""
        if not self.config.enabled:
            # Execute primary function without fallback
            try:
                start_time = time.time()
                result = await primary_func(**kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                return FallbackResult(
                    success=True,
                    fallback_used=False,
                    fallback_type=None,
                    response=result,
                    error_message=None,
                    execution_time_ms=execution_time,
                    attempt_count=1
                )
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                return FallbackResult(
                    success=False,
                    fallback_used=False,
                    fallback_type=None,
                    response=None,
                    error_message=str(e),
                    execution_time_ms=execution_time,
                    attempt_count=1
                )
        
        context = FallbackContext(operation_name, metadata)
        start_time = time.time()
        
        # Try primary function first
        try:
            context.attempt_count += 1
            result = await primary_func(**kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            # Update metrics
            self._update_metrics(True, False, True, execution_time)
            
            # Update strategy metrics
            for strategy in self._strategies:
                strategy.update_metrics(True, False, True)
            
            return FallbackResult(
                success=True,
                fallback_used=False,
                fallback_type=None,
                response=result,
                error_message=None,
                execution_time_ms=execution_time,
                attempt_count=context.attempt_count
            )
            
        except Exception as primary_error:
            _logger.warning("primary_operation_failed", 
                         operation=operation_name, error=str(primary_error))
            
            # Try fallback strategies in order
            for strategy in self._strategies:
                if fallback_types and strategy.get_fallback_type() not in fallback_types:
                    continue
                
                try:
                    context.attempt_count += 1
                    context.fallback_chain.append(strategy.get_fallback_type())
                    
                    fallback_result = await asyncio.wait_for(
                        strategy.execute_fallback(context, primary_error, **kwargs),
                        timeout=self.config.fallback_timeout_seconds
                    )
                    
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Update metrics
                    self._update_metrics(False, True, True, execution_time)
                    strategy.update_metrics(False, True, True)
                    
                    return FallbackResult(
                        success=True,
                        fallback_used=True,
                        fallback_type=strategy.get_fallback_type(),
                        response=fallback_result,
                        error_message=None,
                        execution_time_ms=execution_time,
                        attempt_count=context.attempt_count
                    )
                    
                except Exception as fallback_error:
                    _logger.error("fallback_strategy_failed", 
                                 strategy=strategy.get_fallback_type().value,
                                 error=str(fallback_error))
                    
                    strategy.update_metrics(False, True, False)
                    
                    # Continue to next strategy if retry is enabled
                    if not self.config.retry_on_fallback_failure:
                        continue
            
            # All fallbacks failed
            execution_time = (time.time() - start_time) * 1000
            self._update_metrics(False, False, False, execution_time)
            
            return FallbackResult(
                success=False,
                fallback_used=True,
                fallback_type=None,
                response=None,
                error_message=str(primary_error),
                execution_time_ms=execution_time,
                attempt_count=context.attempt_count
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get fallback manager metrics."""
        with self._metrics_lock:
            total = self._metrics['total_operations']
            
            metrics = self._metrics.copy()
            
            if total > 0:
                metrics['primary_success_rate'] = (self._metrics['primary_success'] / total) * 100
                metrics['fallback_usage_rate'] = (self._metrics['fallback_used'] / total) * 100
                metrics['fallback_success_rate'] = (
                    (self._metrics['fallback_success'] / max(1, self._metrics['fallback_used'])) * 100
                )
            
            if self._execution_times:
                metrics['average_execution_time'] = sum(self._execution_times) / len(self._execution_times)
                metrics['min_execution_time'] = min(self._execution_times)
                metrics['max_execution_time'] = max(self._execution_times)
            
            # Add strategy-specific metrics
            metrics['strategies'] = {}
            for strategy in self._strategies:
                strategy_type = strategy.get_fallback_type().value
                metrics['strategies'][strategy_type] = strategy.get_metrics()
            
            return metrics
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self._metrics_lock:
            self._metrics = {
                'total_operations': 0,
                'primary_success': 0,
                'fallback_used': 0,
                'fallback_success': 0,
                'average_execution_time': 0.0,
            }
            self._execution_times = []
        
        for strategy in self._strategies:
            strategy.metrics = {
                'total_executions': 0,
                'fallback_used': 0,
                'fallback_success': 0,
                'fallback_failure': 0,
                'primary_success': 0,
                'primary_failure': 0,
            }
        
        _logger.info("fallback_metrics_reset")
    
    def _update_metrics(self, 
                      primary_success: bool,
                      fallback_used: bool,
                      operation_success: bool,
                      execution_time: float) -> None:
        """Update internal metrics."""
        with self._metrics_lock:
            self._metrics['total_operations'] += 1
            
            if primary_success:
                self._metrics['primary_success'] += 1
            
            if fallback_used:
                self._metrics['fallback_used'] += 1
                if operation_success:
                    self._metrics['fallback_success'] += 1
            
            self._execution_times.append(execution_time)
            
            # Keep only recent execution times
            if len(self._execution_times) > 1000:
                self._execution_times = self._execution_times[-1000:]
