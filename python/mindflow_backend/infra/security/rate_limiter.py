"""Advanced rate limiting system with distributed support.

Provides global rate limiting with multiple algorithms,
distributed coordination, and intelligent throttling.
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from mindflow_backend.infra.cache.redis_client import get_redis_client
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"


class RateLimitScope(Enum):
    """Rate limiting scopes."""
    GLOBAL = "global"
    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"
    API_KEY = "api_key"
    CUSTOM = "custom"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    scope: RateLimitScope = RateLimitScope.GLOBAL
    limit: int = 100
    window_seconds: int = 60
    burst_size: int | None = None
    refill_rate: float | None = None
    key_extractor: Callable[[dict[str, Any]], str] | None = None
    penalty_multiplier: float = 1.0
    adaptive_threshold: float = 0.8
    enabled: bool = True
    
    def __post_init__(self) -> None:
        if self.burst_size is None:
            self.burst_size = self.limit
        if self.refill_rate is None:
            self.refill_rate = self.limit / self.window_seconds


@dataclass
class RateLimitResult:
    """Rate limiting result."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: float | None = None
    limit: int = 0
    window_seconds: int = 0
    scope: str = ""
    key: str = ""
    reason: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "reset_time": self.reset_time.isoformat(),
            "retry_after": self.retry_after,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "scope": self.scope,
            "key": self.key,
            "reason": self.reason,
        }


class RateLimitAlgorithm(ABC):
    """Abstract base class for rate limiting algorithms."""
    
    @abstractmethod
    async def check_rate_limit(
        self, 
        key: str, 
        config: RateLimitConfig, 
        request_time: datetime | None = None
    ) -> RateLimitResult:
        """Check if request should be rate limited.
        
        Args:
            key: Rate limit key
            config: Rate limit configuration
            request_time: Request timestamp
            
        Returns:
            Rate limiting result
        """
        pass
        
    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset rate limit for key.
        
        Args:
            key: Rate limit key to reset
        """
        pass


class TokenBucketAlgorithm(RateLimitAlgorithm):
    """Token bucket rate limiting algorithm."""
    
    def __init__(self, redis_client):
        """Initialize token bucket algorithm.
        
        Args:
            redis_client: Redis client for distributed storage
        """
        self.redis_client = redis_client
        
    async def check_rate_limit(
        self, 
        key: str, 
        config: RateLimitConfig, 
        request_time: datetime | None = None
    ) -> RateLimitResult:
        """Check token bucket rate limit."""
        if request_time is None:
            request_time = datetime.now(UTC)
            
        redis_key = f"rate_limit:token_bucket:{key}"
        
        # Get current bucket state
        bucket_data = await self.redis_client.get(redis_key)
        
        if bucket_data is None:
            # Initialize new bucket
            tokens = config.burst_size
            last_refill = request_time.timestamp()
        else:
            bucket = json.loads(bucket_data)
            tokens = bucket["tokens"]
            last_refill = bucket["last_refill"]
            
        # Calculate tokens to add based on time elapsed
        current_time = request_time.timestamp()
        time_elapsed = current_time - last_refill
        tokens_to_add = time_elapsed * config.refill_rate
        
        # Refill tokens (don't exceed burst size)
        tokens = min(config.burst_size, tokens + tokens_to_add)
        
        # Check if request can be processed
        if tokens >= 1:
            tokens -= 1
            allowed = True
            remaining = int(tokens)
            retry_after = None
        else:
            allowed = False
            remaining = 0
            # Calculate retry_after based on refill rate
            retry_after = (1 - tokens) / config.refill_rate
            
        # Update bucket state
        bucket_state = {
            "tokens": tokens,
            "last_refill": current_time,
            "config": {
                "limit": config.limit,
                "burst_size": config.burst_size,
                "refill_rate": config.refill_rate,
            }
        }
        
        # Set TTL to window duration
        await self.redis_client.set(redis_key, bucket_state, ttl=config.window_seconds * 2)
        
        reset_time = request_time + timedelta(seconds=config.window_seconds)
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after,
            limit=config.limit,
            window_seconds=config.window_seconds,
            scope=config.scope.value,
            key=key,
            reason="token_bucket" if allowed else "token_bucket_exhausted",
        )
        
    async def reset(self, key: str) -> None:
        """Reset token bucket for key."""
        redis_key = f"rate_limit:token_bucket:{key}"
        await self.redis_client.delete(redis_key)


class SlidingWindowAlgorithm(RateLimitAlgorithm):
    """Sliding window rate limiting algorithm."""
    
    def __init__(self, redis_client):
        """Initialize sliding window algorithm.
        
        Args:
            redis_client: Redis client for distributed storage
        """
        self.redis_client = redis_client
        
    async def check_rate_limit(
        self, 
        key: str, 
        config: RateLimitConfig, 
        request_time: datetime | None = None
    ) -> RateLimitResult:
        """Check sliding window rate limit."""
        if request_time is None:
            request_time = datetime.now(UTC)
            
        redis_key = f"rate_limit:sliding_window:{key}"
        current_time = request_time.timestamp()
        window_start = current_time - config.window_seconds
        
        # Remove old entries outside the window
        await self.redis_client.zremrangebyscore(redis_key, 0, window_start)
        
        # Count current requests in window
        current_count = await self.redis_client.zcard(redis_key)
        
        if current_count < config.limit:
            # Add current request
            await self.redis_client.zadd(redis_key, {str(current_time): current_time})
            await self.redis_client.expire(redis_key, config.window_seconds)
            
            allowed = True
            remaining = config.limit - current_count - 1
            retry_after = None
        else:
            # Rate limited
            allowed = False
            remaining = 0
            
            # Get oldest request to calculate retry_after
            oldest_requests = await self.redis_client.zrange(redis_key, 0, 0, withscores=True)
            if oldest_requests:
                oldest_time = float(oldest_requests[0][1])
                retry_after = oldest_time + config.window_seconds - current_time
            else:
                retry_after = config.window_seconds
                
        reset_time = request_time + timedelta(seconds=config.window_seconds)
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after,
            limit=config.limit,
            window_seconds=config.window_seconds,
            scope=config.scope.value,
            key=key,
            reason="sliding_window" if allowed else "sliding_window_exceeded",
        )
        
    async def reset(self, key: str) -> None:
        """Reset sliding window for key."""
        redis_key = f"rate_limit:sliding_window:{key}"
        await self.redis_client.delete(redis_key)


class FixedWindowAlgorithm(RateLimitAlgorithm):
    """Fixed window rate limiting algorithm."""
    
    def __init__(self, redis_client):
        """Initialize fixed window algorithm.
        
        Args:
            redis_client: Redis client for distributed storage
        """
        self.redis_client = redis_client
        
    async def check_rate_limit(
        self, 
        key: str, 
        config: RateLimitConfig, 
        request_time: datetime | None = None
    ) -> RateLimitResult:
        """Check fixed window rate limit."""
        if request_time is None:
            request_time = datetime.now(UTC)
            
        # Calculate window start time
        window_start = int(request_time.timestamp() // config.window_seconds) * config.window_seconds
        window_key = f"rate_limit:fixed_window:{key}:{window_start}"
        
        # Get current count
        current_count = await self.redis_client.incr(window_key)
        
        # Set TTL for the window
        if current_count == 1:
            await self.redis_client.expire(window_key, config.window_seconds)
            
        if current_count <= config.limit:
            allowed = True
            remaining = config.limit - current_count
            retry_after = None
        else:
            allowed = False
            remaining = 0
            # Calculate retry_after as remaining time in window
            window_end = window_start + config.window_seconds
            retry_after = window_end - request_time.timestamp()
            
        reset_time = datetime.fromtimestamp(window_start + config.window_seconds, UTC)
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after,
            limit=config.limit,
            window_seconds=config.window_seconds,
            scope=config.scope.value,
            key=key,
            reason="fixed_window" if allowed else "fixed_window_exceeded",
        )
        
    async def reset(self, key: str) -> None:
        """Reset fixed window for key."""
        # This is more complex for fixed windows as we need to find the current window
        current_time = datetime.now(UTC)
        window_start = int(current_time.timestamp() // 60) * 60  # Assuming 60s windows
        window_key = f"rate_limit:fixed_window:{key}:{window_start}"
        await self.redis_client.delete(window_key)


class AdaptiveAlgorithm(RateLimitAlgorithm):
    """Adaptive rate limiting algorithm that adjusts based on load."""
    
    def __init__(self, redis_client):
        """Initialize adaptive algorithm.
        
        Args:
            redis_client: Redis client for distributed storage
        """
        self.redis_client = redis_client
        self.base_algorithm = TokenBucketAlgorithm(redis_client)
        
    async def check_rate_limit(
        self, 
        key: str, 
        config: RateLimitConfig, 
        request_time: datetime | None = None
    ) -> RateLimitResult:
        """Check adaptive rate limit."""
        # Get system load metrics
        load_metrics = await self._get_load_metrics()
        
        # Adjust limit based on load
        if load_metrics.get("cpu_utilization", 0) > config.adaptive_threshold:
            adjusted_limit = int(config.limit * (1 - config.penalty_multiplier))
        elif load_metrics.get("error_rate", 0) > 0.1:
            adjusted_limit = int(config.limit * 0.5)
        else:
            adjusted_limit = config.limit
            
        # Create adjusted config
        adjusted_config = RateLimitConfig(
            algorithm=config.algorithm,
            scope=config.scope,
            limit=adjusted_limit,
            window_seconds=config.window_seconds,
            burst_size=min(config.burst_size, adjusted_limit),
            refill_rate=adjusted_limit / config.window_seconds,
        )
        
        # Use base algorithm with adjusted config
        result = await self.base_algorithm.check_rate_limit(key, adjusted_config, request_time)
        result.reason = f"adaptive_{result.reason}"
        
        return result
        
    async def reset(self, key: str) -> None:
        """Reset adaptive rate limit for key."""
        await self.base_algorithm.reset(key)
        
    async def _get_load_metrics(self) -> dict[str, float]:
        """Get system load metrics for adaptive adjustments."""
        # This would integrate with monitoring system
        # For now, return dummy metrics
        return {
            "cpu_utilization": 0.5,
            "memory_utilization": 0.6,
            "error_rate": 0.02,
            "response_time_ms": 150.0,
        }


class RateLimiter:
    """Advanced rate limiting system.
    
    Features:
    - Multiple rate limiting algorithms
    - Distributed coordination via Redis
    - Multiple scopes (global, user, IP, endpoint)
    - Adaptive rate limiting
    - Performance metrics
    - Graceful degradation
    """
    
    def __init__(self):
        """Initialize rate limiter."""
        self._algorithms: dict[RateLimitAlgorithm, RateLimitAlgorithm] = {}
        self._configs: dict[str, RateLimitConfig] = {}
        self._redis_client = None
        self._is_initialized = False
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "algorithm_usage": {},
            "scope_usage": {},
        }
        
    async def initialize(self) -> None:
        """Initialize rate limiter."""
        self._redis_client = get_redis_client()
        await self._redis_client.initialize()
        
        # Initialize algorithms
        self._algorithms[RateLimitAlgorithm.TOKEN_BUCKET] = TokenBucketAlgorithm(self._redis_client)
        self._algorithms[RateLimitAlgorithm.SLIDING_WINDOW] = SlidingWindowAlgorithm(self._redis_client)
        self._algorithms[RateLimitAlgorithm.FIXED_WINDOW] = FixedWindowAlgorithm(self._redis_client)
        self._algorithms[RateLimitAlgorithm.LEAKY_BUCKET] = TokenBucketAlgorithm(self._redis_client)  # Reuse token bucket
        self._algorithms[RateLimitAlgorithm.ADAPTIVE] = AdaptiveAlgorithm(self._redis_client)
        
        self._is_initialized = True
        
        _logger.info(
            "rate_limiter_initialized",
            algorithms_count=len(self._algorithms),
            redis_connected=self._redis_client.is_connected(),
        )
        
    def add_config(self, name: str, config: RateLimitConfig) -> None:
        """Add rate limit configuration.
        
        Args:
            name: Configuration name
            config: Rate limit configuration
        """
        self._configs[name] = config
        _logger.debug("rate_limit_config_added", name=name, algorithm=config.algorithm.value)
        
    def remove_config(self, name: str) -> bool:
        """Remove rate limit configuration.
        
        Args:
            name: Configuration name
            
        Returns:
            True if configuration was removed
        """
        if name in self._configs:
            del self._configs[name]
            _logger.debug("rate_limit_config_removed", name=name)
            return True
        return False
        
    async def check_rate_limit(
        self,
        config_name: str,
        context: dict[str, Any],
        request_time: datetime | None = None
    ) -> RateLimitResult:
        """Check rate limit for given configuration and context.
        
        Args:
            config_name: Configuration name
            context: Request context (user_id, ip, endpoint, etc.)
            request_time: Request timestamp
            
        Returns:
            Rate limiting result
        """
        if not self._is_initialized:
            raise RuntimeError("Rate limiter not initialized")
            
        config = self._configs.get(config_name)
        if not config or not config.enabled:
            # Return allowed result if no config or disabled
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_time=datetime.now(UTC) + timedelta(hours=1),
                limit=999999,
                window_seconds=3600,
                scope="disabled",
                key="none",
                reason="no_config",
            )
            
        # Extract rate limit key
        key = self._extract_key(config, context)
        
        # Get algorithm
        algorithm = self._algorithms.get(config.algorithm)
        if not algorithm:
            raise ValueError(f"Unknown algorithm: {config.algorithm}")
            
        # Check rate limit
        start_time = time.time()
        result = await algorithm.check_rate_limit(key, config, request_time)
        duration_ms = (time.time() - start_time) * 1000
        
        # Update statistics
        self._stats["total_requests"] += 1
        if result.allowed:
            self._stats["allowed_requests"] += 1
        else:
            self._stats["blocked_requests"] += 1
            
        # Update algorithm usage
        algo_name = config.algorithm.value
        self._stats["algorithm_usage"][algo_name] = self._stats["algorithm_usage"].get(algo_name, 0) + 1
        
        # Update scope usage
        scope_name = config.scope.value
        self._stats["scope_usage"][scope_name] = self._stats["scope_usage"].get(scope_name, 0) + 1
        
        _logger.debug(
            "rate_limit_checked",
            config=config_name,
            key=key,
            allowed=result.allowed,
            remaining=result.remaining,
            duration_ms=duration_ms,
        )
        
        return result
        
    def _extract_key(self, config: RateLimitConfig, context: dict[str, Any]) -> str:
        """Extract rate limit key from context.
        
        Args:
            config: Rate limit configuration
            context: Request context
            
        Returns:
            Rate limit key
        """
        if config.key_extractor:
            return config.key_extractor(context)
            
        # Default key extraction based on scope
        if config.scope == RateLimitScope.GLOBAL:
            return "global"
        elif config.scope == RateLimitScope.USER:
            user_id = context.get("user_id", "anonymous")
            return f"user:{user_id}"
        elif config.scope == RateLimitScope.IP:
            ip = context.get("ip", "unknown")
            return f"ip:{ip}"
        elif config.scope == RateLimitScope.ENDPOINT:
            endpoint = context.get("endpoint", "unknown")
            method = context.get("method", "unknown")
            return f"endpoint:{method}:{endpoint}"
        elif config.scope == RateLimitScope.API_KEY:
            api_key = context.get("api_key", "unknown")
            return f"api_key:{api_key}"
        else:
            # Custom scope - use all context
            context_str = json.dumps(context, sort_keys=True)
            return f"custom:{hashlib.md5(context_str.encode()).hexdigest()}"
            
    async def reset_rate_limit(self, config_name: str, context: dict[str, Any]) -> bool:
        """Reset rate limit for given configuration and context.
        
        Args:
            config_name: Configuration name
            context: Request context
            
        Returns:
            True if reset was successful
        """
        config = self._configs.get(config_name)
        if not config:
            return False
            
        key = self._extract_key(config, context)
        algorithm = self._algorithms.get(config.algorithm)
        
        if algorithm:
            await algorithm.reset(key)
            _logger.info("rate_limit_reset", config=config_name, key=key)
            return True
            
        return False
        
    def get_stats(self) -> dict[str, Any]:
        """Get rate limiting statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Calculate rates
        total_requests = stats["total_requests"]
        if total_requests > 0:
            stats["allowed_rate"] = stats["allowed_requests"] / total_requests
            stats["blocked_rate"] = stats["blocked_requests"] / total_requests
        else:
            stats["allowed_rate"] = 0.0
            stats["blocked_rate"] = 0.0
            
        # Add configuration info
        stats["configs"] = {
            name: {
                "algorithm": config.algorithm.value,
                "scope": config.scope.value,
                "limit": config.limit,
                "window_seconds": config.window_seconds,
                "enabled": config.enabled,
            }
            for name, config in self._configs.items()
        }
        
        return stats
        
    async def health_check(self) -> dict[str, Any]:
        """Perform rate limiter health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test Redis connection
            redis_health = await self._redis_client.health_check()
            
            # Test rate limit functionality
            test_context = {"user_id": "health_check", "endpoint": "/health"}
            test_result = await self.check_rate_limit("default", test_context)
            
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "redis_status": redis_health.get("status", "unknown"),
                "test_rate_limit": test_result.allowed,
                "duration_ms": duration_ms,
                "configs_count": len(self._configs),
                "algorithms_count": len(self._algorithms),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("rate_limiter_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("rate_limiter_health_check_failed", **error_data)
            return error_data


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance.
    
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
