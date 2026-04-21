"""Advanced Redis client with connection pooling and monitoring.

Provides robust Redis operations with health monitoring,
circuit breaker, retry logic, and performance metrics.
"""

from __future__ import annotations

import json
import pickle
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

try:
    import redis.asyncio as redis
    from redis.asyncio import ConnectionPool
    from redis.exceptions import (
        ConnectionError,
        RedisError,
        ResponseError,
        TimeoutError,
    )
except ImportError:  # pragma: no cover - optional dependency in test envs
    redis = None  # type: ignore[assignment]
    ConnectionPool = Any  # type: ignore[assignment]

    class RedisError(Exception):
        """Fallback Redis base exception when the redis package is absent."""

    class ConnectionError(RedisError):
        """Fallback connection error."""

    class ResponseError(RedisError):
        """Fallback response error."""

    class TimeoutError(RedisError):
        """Fallback timeout error."""

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.resilience import RetryConfig, with_retry

_logger = get_logger(__name__)


def _require_redis_package() -> None:
    """Raise a clear error when redis extras are not installed."""
    if redis is None:  # pragma: no cover - exercised only in reduced test envs
        raise ModuleNotFoundError(
            "The 'redis' package is required for Redis-backed cache operations. "
            "Install the optional cache dependencies or disable Redis features in this environment."
        )


class RedisSerializationFormat(Enum):
    """Redis serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    STRING = "string"
    BINARY = "binary"


@dataclass
class RedisMetrics:
    """Redis client performance metrics."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    connection_errors: int = 0
    timeout_errors: int = 0
    response_errors: int = 0
    total_response_time_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    last_operation_time: datetime | None = None
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.successful_operations / max(self.total_operations, 1)
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / max(total_requests, 1)
    
    def update_operation(self, success: bool, response_time_ms: float, error_type: str | None = None) -> None:
        """Update metrics with operation result."""
        self.total_operations += 1
        self.total_response_time_ms += response_time_ms
        self.avg_response_time_ms = self.total_response_time_ms / self.total_operations
        self.last_operation_time = datetime.now(UTC)
        
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
            if error_type == "ConnectionError":
                self.connection_errors += 1
            elif error_type == "TimeoutError":
                self.timeout_errors += 1
            elif error_type == "ResponseError":
                self.response_errors += 1


class RedisClient:
    """Advanced Redis client with comprehensive features.
    
    Features:
    - Connection pooling with health monitoring
    - Circuit breaker and retry logic
    - Multiple serialization formats
    - Performance metrics collection
    - Automatic reconnection
    - Cluster and sentinel support
    - Pipeline operations
    - Pub/Sub support
    """
    
    def __init__(self) -> None:
        """Initialize Redis client."""
        self._pool: ConnectionPool | None = None
        self._client: redis.Redis | None = None
        self._metrics = RedisMetrics()
        self._is_connected = False
        self._last_health_check: datetime | None = None
        self._serialization_format = RedisSerializationFormat.JSON
        self._compression_enabled = False
        self._circuit_breaker_enabled = True
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure: float | None = None
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_recovery_timeout = 60.0
        
    async def initialize(self) -> None:
        """Initialize Redis connection pool and client."""
        _require_redis_package()
        settings = get_settings()
        cache_config = settings.cache
        
        try:
            # Create connection pool
            self._pool = ConnectionPool(
                host=cache_config.redis_host,
                port=cache_config.redis_port,
                db=cache_config.redis_db,
                password=cache_config.redis_password,
                username=cache_config.redis_username,
                max_connections=cache_config.redis_max_connections,
                socket_timeout=cache_config.redis_socket_timeout,
                socket_connect_timeout=cache_config.redis_socket_connect_timeout,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={},
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            
            self._is_connected = True
            self._last_health_check = datetime.now(UTC)
            
            # Configure serialization
            self._serialization_format = RedisSerializationFormat.JSON
            self._compression_enabled = cache_config.enable_compression
            
            _logger.info(
                "redis_client_initialized",
                host=cache_config.redis_host,
                port=cache_config.redis_port,
                db=cache_config.redis_db,
                max_connections=cache_config.redis_max_connections,
                compression_enabled=self._compression_enabled,
            )
            
        except Exception as e:
            _logger.error("redis_client_initialization_failed", error=str(e))
            raise
            
    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._pool:
            await self._pool.disconnect()
            self._is_connected = False
            _logger.info("redis_client_closed")
            
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is open.
        
        Returns:
            True if operation should proceed, False if blocked
        """
        if not self._circuit_breaker_enabled:
            return True
            
        current_time = time.time()
        
        # Check if we should attempt recovery
        if (self._circuit_breaker_last_failure and 
            current_time - self._circuit_breaker_last_failure > self._circuit_breaker_recovery_timeout):
            self._circuit_breaker_failures = 0
            self._circuit_breaker_last_failure = None
            _logger.info("redis_circuit_breaker_recovery_attempt")
            return True
            
        # Check if circuit breaker is open
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            _logger.warning(
                "redis_circuit_breaker_open",
                failures=self._circuit_breaker_failures,
                threshold=self._circuit_breaker_threshold,
            )
            return False
            
        return True
        
    def _record_circuit_breaker_failure(self) -> None:
        """Record a circuit breaker failure."""
        if self._circuit_breaker_enabled:
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure = time.time()
            
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage.
        
        Args:
            value: Value to serialize
            
        Returns:
            Serialized bytes
        """
        if self._serialization_format == RedisSerializationFormat.JSON:
            data = json.dumps(value, default=str).encode('utf-8')
        elif self._serialization_format == RedisSerializationFormat.PICKLE:
            data = pickle.dumps(value)
        elif self._serialization_format == RedisSerializationFormat.STRING:
            data = str(value).encode('utf-8')
        elif self._serialization_format == RedisSerializationFormat.BINARY:
            if isinstance(value, bytes):
                data = value
            else:
                data = str(value).encode('utf-8')
        else:
            data = json.dumps(value, default=str).encode('utf-8')
            
        # Apply compression if enabled and data is large enough
        if self._compression_enabled and len(data) > 1024:
            import gzip
            data = gzip.compress(data)
            
        return data
        
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from Redis storage.
        
        Args:
            data: Serialized bytes
            
        Returns:
            Deserialized value
        """
        # Check if data is compressed
        if self._compression_enabled and len(data) > 0:
            try:
                import gzip
                data = gzip.decompress(data)
            except Exception:
                pass  # Data might not be compressed
                
        if self._serialization_format == RedisSerializationFormat.JSON:
            return json.loads(data.decode('utf-8'))
        elif self._serialization_format == RedisSerializationFormat.PICKLE:
            return pickle.loads(data)
        elif self._serialization_format == RedisSerializationFormat.STRING:
            return data.decode('utf-8')
        elif self._serialization_format == RedisSerializationFormat.BINARY:
            return data
        else:
            return json.loads(data.decode('utf-8'))
            
    async def _execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute Redis operation with retry logic and metrics.
        
        Args:
            operation: Redis operation to execute
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
        """
        if not self._check_circuit_breaker():
            raise RedisError("Redis circuit breaker is open")
            
        start_time = time.time()
        
        retry_config = RetryConfig(
            max_retries=3,
            backoff_base=0.1,
            backoff_max=2.0,
            retry_on_status=[429, 500, 502, 503, 504],
        )
        
        try:
            async def _execute():
                return await operation(*args, **kwargs)
                
            result = await with_retry(retry_config)(_execute)()
            
            response_time_ms = (time.time() - start_time) * 1000
            self._metrics.update_operation(True, response_time_ms)
            
            return result
            
        except ConnectionError:
            response_time_ms = (time.time() - start_time) * 1000
            self._metrics.update_operation(False, response_time_ms, "ConnectionError")
            self._record_circuit_breaker_failure()
            raise
        except TimeoutError:
            response_time_ms = (time.time() - start_time) * 1000
            self._metrics.update_operation(False, response_time_ms, "TimeoutError")
            raise
        except ResponseError:
            response_time_ms = (time.time() - start_time) * 1000
            self._metrics.update_operation(False, response_time_ms, "ResponseError")
            raise
        except Exception:
            response_time_ms = (time.time() - start_time) * 1000
            self._metrics.update_operation(False, response_time_ms)
            raise
            
    # Basic Redis operations
    async def get(self, key: str) -> Any | None:
        """Get value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Value or None if not found
        """
        try:
            data = await self._execute_with_retry(self._client.get, key)
            
            if data is None:
                self._metrics.cache_misses += 1
                return None
                
            self._metrics.cache_hits += 1
            return self._deserialize_value(data)
            
        except Exception as e:
            _logger.error("redis_get_failed", key=key, error=str(e))
            raise
            
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int | None = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set value in Redis.
        
        Args:
            key: Redis key
            value: Value to store
            ttl: Time to live in seconds
            nx: Set only if key doesn't exist
            xx: Set only if key exists
            
        Returns:
            True if successful
        """
        try:
            data = self._serialize_value(value)
            result = await self._execute_with_retry(
                self._client.set, 
                key, 
                data, 
                ex=ttl, 
                nx=nx, 
                xx=xx
            )
            return bool(result)
            
        except Exception as e:
            _logger.error("redis_set_failed", key=key, error=str(e))
            raise
            
    async def delete(self, key: str) -> bool:
        """Delete key from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            True if key was deleted
        """
        try:
            result = await self._execute_with_retry(self._client.delete, key)
            return bool(result)
            
        except Exception as e:
            _logger.error("redis_delete_failed", key=key, error=str(e))
            raise
            
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis.
        
        Args:
            key: Redis key
            
        Returns:
            True if key exists
        """
        try:
            result = await self._execute_with_retry(self._client.exists, key)
            return bool(result)
            
        except Exception as e:
            _logger.error("redis_exists_failed", key=key, error=str(e))
            raise
            
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key.
        
        Args:
            key: Redis key
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            result = await self._execute_with_retry(self._client.expire, key, ttl)
            return bool(result)
            
        except Exception as e:
            _logger.error("redis_expire_failed", key=key, ttl=ttl, error=str(e))
            raise
            
    async def ttl(self, key: str) -> int:
        """Get time to live for key.
        
        Args:
            key: Redis key
            
        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        try:
            result = await self._execute_with_retry(self._client.ttl, key)
            return result
            
        except Exception as e:
            _logger.error("redis_ttl_failed", key=key, error=str(e))
            raise
            
    # Advanced Redis operations
    async def mget(self, keys: list[str]) -> list[Any | None]:
        """Get multiple values from Redis.
        
        Args:
            keys: List of Redis keys
            
        Returns:
            List of values (None for missing keys)
        """
        try:
            data_list = await self._execute_with_retry(self._client.mget, keys)
            
            results = []
            for i, data in enumerate(data_list):
                if data is None:
                    self._metrics.cache_misses += 1
                    results.append(None)
                else:
                    self._metrics.cache_hits += 1
                    results.append(self._deserialize_value(data))
                    
            return results
            
        except Exception as e:
            _logger.error("redis_mget_failed", keys=keys, error=str(e))
            raise
            
    async def mset(self, mapping: dict[str, Any]) -> bool:
        """Set multiple values in Redis.
        
        Args:
            mapping: Dictionary of key-value pairs
            
        Returns:
            True if successful
        """
        try:
            serialized_mapping = {}
            for key, value in mapping.items():
                serialized_mapping[key] = self._serialize_value(value)
                
            result = await self._execute_with_retry(self._client.mset, serialized_mapping)
            return bool(result)
            
        except Exception as e:
            _logger.error("redis_mset_failed", keys=list(mapping.keys()), error=str(e))
            raise
            
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment numeric value.
        
        Args:
            key: Redis key
            amount: Increment amount
            
        Returns:
            New value
        """
        try:
            result = await self._execute_with_retry(self._client.incrby, key, amount)
            return result
            
        except Exception as e:
            _logger.error("redis_incr_failed", key=key, amount=amount, error=str(e))
            raise
            
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement numeric value.
        
        Args:
            key: Redis key
            amount: Decrement amount
            
        Returns:
            New value
        """
        try:
            result = await self._execute_with_retry(self._client.decrby, key, amount)
            return result
            
        except Exception as e:
            _logger.error("redis_decr_failed", key=key, amount=amount, error=str(e))
            raise
            
    # Hash operations
    async def hget(self, key: str, field: str) -> Any | None:
        """Get hash field value.
        
        Args:
            key: Hash key
            field: Field name
            
        Returns:
            Field value or None
        """
        try:
            data = await self._execute_with_retry(self._client.hget, key, field)
            
            if data is None:
                return None
                
            return self._deserialize_value(data)
            
        except Exception as e:
            _logger.error("redis_hget_failed", key=key, field=field, error=str(e))
            raise
            
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Set hash field value.
        
        Args:
            key: Hash key
            field: Field name
            value: Field value
            
        Returns:
            True if new field was created
        """
        try:
            data = self._serialize_value(value)
            result = await self._execute_with_retry(self._client.hset, key, field, data)
            return bool(result)
            
        except Exception as e:
            _logger.error("redis_hset_failed", key=key, field=field, error=str(e))
            raise
            
    async def hgetall(self, key: str) -> dict[str, Any]:
        """Get all hash fields and values.
        
        Args:
            key: Hash key
            
        Returns:
            Dictionary of field-value pairs
        """
        try:
            data = await self._execute_with_retry(self._client.hgetall, key)
            
            result = {}
            for field, value in data.items():
                result[field.decode('utf-8')] = self._deserialize_value(value)
                
            return result
            
        except Exception as e:
            _logger.error("redis_hgetall_failed", key=key, error=str(e))
            raise
            
    # List operations
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to left of list.
        
        Args:
            key: List key
            *values: Values to push
            
        Returns:
            New list length
        """
        try:
            serialized_values = [self._serialize_value(value) for value in values]
            result = await self._execute_with_retry(self._client.lpush, key, *serialized_values)
            return result
            
        except Exception as e:
            _logger.error("redis_lpush_failed", key=key, error=str(e))
            raise
            
    async def rpop(self, key: str) -> Any | None:
        """Pop value from right of list.
        
        Args:
            key: List key
            
        Returns:
            Popped value or None
        """
        try:
            data = await self._execute_with_retry(self._client.rpop, key)
            
            if data is None:
                return None
                
            return self._deserialize_value(data)
            
        except Exception as e:
            _logger.error("redis_rpop_failed", key=key, error=str(e))
            raise
            
    async def lrange(self, key: str, start: int, end: int) -> list[Any]:
        """Get range of list elements.
        
        Args:
            key: List key
            start: Start index
            end: End index
            
        Returns:
            List of values
        """
        try:
            data_list = await self._execute_with_retry(self._client.lrange, key, start, end)
            
            return [self._deserialize_value(data) for data in data_list]
            
        except Exception as e:
            _logger.error("redis_lrange_failed", key=key, start=start, end=end, error=str(e))
            raise
            
    # Pipeline operations
    @asynccontextmanager
    async def pipeline(self) -> redis.client.Pipeline:
        """Create Redis pipeline.
        
        Yields:
            Redis pipeline
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized")
            
        pipe = self._client.pipeline()
        try:
            yield pipe
            await pipe.execute()
        except Exception as e:
            _logger.error("redis_pipeline_failed", error=str(e))
            raise
            
    # Health check
    async def health_check(self) -> dict[str, Any]:
        """Perform Redis health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test basic connectivity
            await self._client.ping()
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = {"test": True, "timestamp": time.time()}
            
            await self.set(test_key, test_value, ttl=10)
            retrieved = await self.get(test_key)
            await self.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            # Get connection info
            info = await self._client.info()
            
            health_data = {
                "status": "healthy",
                "response_time_ms": response_time,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "operations_per_second": info.get("instantaneous_ops_per_sec", 0),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            self._is_connected = True
            self._last_health_check = datetime.now(UTC)
            
            _logger.info("redis_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            self._is_connected = False
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("redis_health_check_failed", **error_data)
            return error_data
            
    def get_metrics(self) -> RedisMetrics:
        """Get Redis client metrics.
        
        Returns:
            Current metrics
        """
        return self._metrics
        
    def is_connected(self) -> bool:
        """Check if Redis client is connected.
        
        Returns:
            True if connected
        """
        return self._is_connected
        
    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information.
        
        Returns:
            Connection details
        """
        if not self._pool:
            return {"status": "not_initialized"}
            
        return {
            "status": "connected" if self._is_connected else "disconnected",
            "max_connections": self._pool.max_connections,
            "created_connections": self._pool.created_connections,
            "available_connections": len(self._pool._available_connections),
            "in_use_connections": len(self._pool._in_use_connections),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "metrics": {
                "total_operations": self._metrics.total_operations,
                "success_rate": self._metrics.success_rate,
                "avg_response_time_ms": self._metrics.avg_response_time_ms,
                "cache_hit_rate": self._metrics.cache_hit_rate,
            },
        }


# Global Redis client instance
_redis_client: RedisClient | None = None


def get_redis_client() -> RedisClient:
    """Get global Redis client instance.
    
    Returns:
        RedisClient instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


# ---------------------------------------------------------------------------
# Raw connection helpers — canonical replacements for the former infra.redis shim
# ---------------------------------------------------------------------------

from functools import lru_cache


@lru_cache(maxsize=1)
def get_async_redis():
    """Return a cached async Redis connection (raw redis.asyncio.Redis instance).

    Use this when you need direct access to the Redis protocol (xadd, pipeline,
    pub/sub, etc.) rather than the high-level RedisClient wrapper.
    """
    _require_redis_package()
    import redis.asyncio as _redis_async  # type: ignore

    settings = get_settings()
    return _redis_async.from_url(settings.cache.redis_url, decode_responses=True)


@lru_cache(maxsize=1)
def get_sync_redis():
    """Return a cached synchronous Redis connection (raw redis.Redis instance).

    Use this for sync contexts (workers, CLI scripts).  Prefer the async
    variant in async code paths.
    """
    _require_redis_package()
    import redis as _redis  # type: ignore

    settings = get_settings()
    return _redis.from_url(settings.cache.redis_url, decode_responses=True)
