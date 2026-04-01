"""Advanced cache invalidation patterns and strategies.

Provides comprehensive cache invalidation with multiple strategies,
dependency tracking, and automatic invalidation.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from mindflow_backend.infra.cache.cache_manager import get_cache_manager
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    IMMEDIATE = "immediate"              # Invalidate immediately
    DELAYED = "delayed"                  # Invalidate after delay
    BATCHED = "batched"                  # Batch invalidations
    CONDITIONAL = "conditional"          # Invalidate based on conditions
    CASCADE = "cascade"                  # Cascade invalidations
    DEPENDENCY_BASED = "dependency_based" # Based on dependencies


class InvalidationTrigger(Enum):
    """Cache invalidation triggers."""
    MANUAL = "manual"                    # Manual invalidation
    TIME_BASED = "time_based"            # Time-based expiration
    EVENT_BASED = "event_based"          # Event-driven
    DATA_CHANGE = "data_change"          # Data change detected
    SIZE_LIMIT = "size_limit"            # Size limit exceeded
    CUSTOM = "custom"                    # Custom trigger


@dataclass
class InvalidationRule:
    """Cache invalidation rule definition."""
    name: str
    pattern: str                         # Key pattern to match
    strategy: InvalidationStrategy = InvalidationStrategy.IMMEDIATE
    trigger: InvalidationTrigger = InvalidationTrigger.MANUAL
    priority: int = 1                    # Higher priority = executed first
    conditions: dict[str, Any] = field(default_factory=dict)
    delay_seconds: float = 0.0
    batch_size: int = 100
    cascade_rules: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_triggered: datetime | None = None
    trigger_count: int = 0
    invalidation_count: int = 0
    
    def should_trigger(self, context: dict[str, Any]) -> bool:
        """Check if rule should be triggered.
        
        Args:
            context: Invalidation context
            
        Returns:
            True if rule should trigger
        """
        if not self.enabled:
            return False
            
        # Check conditions
        for key, expected_value in self.conditions.items():
            if key not in context:
                return False
                
            actual_value = context[key]
            
            if isinstance(expected_value, dict):
                operator = expected_value.get("operator", "equals")
                value = expected_value.get("value")
                
                if operator == "equals":
                    if actual_value != value:
                        return False
                elif operator == "contains":
                    if value not in str(actual_value):
                        return False
                elif operator == "in":
                    if actual_value not in value:
                        return False
                elif operator == "greater_than":
                    if actual_value <= value:
                        return False
                elif operator == "less_than":
                    if actual_value >= value:
                        return False
            else:
                if actual_value != expected_value:
                    return False
                    
        return True


@dataclass
class InvalidationEvent:
    """Cache invalidation event."""
    id: str
    rule_name: str
    pattern: str
    strategy: InvalidationStrategy
    trigger: InvalidationTrigger
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    scheduled_at: datetime | None = None
    executed_at: datetime | None = None
    affected_keys: list[str] = field(default_factory=list)
    success: bool | None = None
    error_message: str | None = None
    duration_ms: float = 0.0


class DependencyTracker:
    """Tracks cache dependencies for intelligent invalidation."""
    
    def __init__(self):
        """Initialize dependency tracker."""
        self._dependencies: dict[str, set[str]] = {}  # key -> dependencies
        self._dependents: dict[str, set[str]] = {}     # key -> dependents
        self._lock = asyncio.Lock()
        
    async def add_dependency(self, key: str, dependency: str) -> None:
        """Add dependency relationship.
        
        Args:
            key: Cache key
            dependency: Dependency key
        """
        async with self._lock:
            if key not in self._dependencies:
                self._dependencies[key] = set()
            self._dependencies[key].add(dependency)
            
            if dependency not in self._dependents:
                self._dependents[dependency] = set()
            self._dependents[dependency].add(key)
            
    async def remove_dependency(self, key: str, dependency: str) -> None:
        """Remove dependency relationship.
        
        Args:
            key: Cache key
            dependency: Dependency key
        """
        async with self._lock:
            if key in self._dependencies:
                self._dependencies[key].discard(dependency)
                if not self._dependencies[key]:
                    del self._dependencies[key]
                    
            if dependency in self._dependents:
                self._dependents[dependency].discard(key)
                if not self._dependents[dependency]:
                    del self._dependents[dependency]
                    
    async def get_dependents(self, key: str) -> set[str]:
        """Get all dependents of a key.
        
        Args:
            key: Cache key
            
        Returns:
            Set of dependent keys
        """
        async with self._lock:
            return self._dependents.get(key, set()).copy()
            
    async def get_dependencies(self, key: str) -> set[str]:
        """Get all dependencies of a key.
        
        Args:
            key: Cache key
            
        Returns:
            Set of dependency keys
        """
        async with self._lock:
            return self._dependencies.get(key, set()).copy()
            
    async def get_all_dependents(self, key: str) -> set[str]:
        """Get all transitive dependents of a key.
        
        Args:
            key: Cache key
            
        Returns:
            Set of all dependent keys
        """
        async with self._lock:
            all_dependents = set()
            to_process = [key]
            
            while to_process:
                current = to_process.pop()
                dependents = self._dependents.get(current, set())
                
                for dependent in dependents:
                    if dependent not in all_dependents:
                        all_dependents.add(dependent)
                        to_process.append(dependent)
                        
            return all_dependents


class BaseInvalidationStrategy(ABC):
    """Abstract base class for invalidation strategies."""

    @abstractmethod
    async def execute(self, keys: list[str], context: dict[str, Any]) -> dict[str, Any]:
        """Execute invalidation strategy.

        Args:
            keys: Keys to invalidate
            context: Invalidation context

        Returns:
            Invalidation result
        """
        pass


class ImmediateInvalidationStrategy(BaseInvalidationStrategy):
    """Immediate cache invalidation."""
    
    async def execute(self, keys: list[str], context: dict[str, Any]) -> dict[str, Any]:
        """Execute immediate invalidation."""
        cache_manager = get_cache_manager()
        
        results = {
            "invalidated_keys": [],
            "failed_keys": [],
            "duration_ms": 0.0,
        }
        
        start_time = time.time()
        
        for key in keys:
            try:
                success = await cache_manager.delete(key)
                if success:
                    results["invalidated_keys"].append(key)
                else:
                    results["failed_keys"].append(key)
            except Exception as e:
                _logger.error("immediate_invalidation_failed", key=key, error=str(e))
                results["failed_keys"].append(key)
                
        results["duration_ms"] = (time.time() - start_time) * 1000
        
        return results


class DelayedInvalidationStrategy(BaseInvalidationStrategy):
    """Delayed cache invalidation."""
    
    def __init__(self, delay_seconds: float):
        """Initialize delayed invalidation.
        
        Args:
            delay_seconds: Delay before invalidation
        """
        self.delay_seconds = delay_seconds
        
    async def execute(self, keys: list[str], context: dict[str, Any]) -> dict[str, Any]:
        """Execute delayed invalidation."""
        await asyncio.sleep(self.delay_seconds)
        
        # Use immediate strategy after delay
        immediate_strategy = ImmediateInvalidationStrategy()
        return await immediate_strategy.execute(keys, context)


class BatchedInvalidationStrategy(BaseInvalidationStrategy):
    """Batched cache invalidation."""
    
    def __init__(self, batch_size: int = 100):
        """Initialize batched invalidation.
        
        Args:
            batch_size: Size of each batch
        """
        self.batch_size = batch_size
        
    async def execute(self, keys: list[str], context: dict[str, Any]) -> dict[str, Any]:
        """Execute batched invalidation."""
        cache_manager = get_cache_manager()
        
        results = {
            "invalidated_keys": [],
            "failed_keys": [],
            "batches_processed": 0,
            "duration_ms": 0.0,
        }
        
        start_time = time.time()
        
        # Process in batches
        for i in range(0, len(keys), self.batch_size):
            batch_keys = keys[i:i + self.batch_size]
            
            try:
                # Use Redis pipeline for batch operations
                async with cache_manager._l2_cache.redis_client.pipeline() as pipe:
                    for key in batch_keys:
                        pipe.delete(key)
                    
                    batch_results = await pipe.execute()
                    
                    for j, success in enumerate(batch_results):
                        if success:
                            results["invalidated_keys"].append(batch_keys[j])
                        else:
                            results["failed_keys"].append(batch_keys[j])
                            
                results["batches_processed"] += 1
                
            except Exception as e:
                _logger.error("batch_invalidation_failed", batch_start=i, error=str(e))
                results["failed_keys"].extend(batch_keys)
                
        results["duration_ms"] = (time.time() - start_time) * 1000
        
        return results


class ConditionalInvalidationStrategy(BaseInvalidationStrategy):
    """Conditional cache invalidation."""
    
    def __init__(self, condition: Callable[[str, dict[str, Any]], bool]):
        """Initialize conditional invalidation.
        
        Args:
            condition: Function that determines if key should be invalidated
        """
        self.condition = condition
        
    async def execute(self, keys: list[str], context: dict[str, Any]) -> dict[str, Any]:
        """Execute conditional invalidation."""
        cache_manager = get_cache_manager()
        
        results = {
            "invalidated_keys": [],
            "skipped_keys": [],
            "failed_keys": [],
            "duration_ms": 0.0,
        }
        
        start_time = time.time()
        
        for key in keys:
            try:
                if self.condition(key, context):
                    success = await cache_manager.delete(key)
                    if success:
                        results["invalidated_keys"].append(key)
                    else:
                        results["failed_keys"].append(key)
                else:
                    results["skipped_keys"].append(key)
            except Exception as e:
                _logger.error("conditional_invalidation_failed", key=key, error=str(e))
                results["failed_keys"].append(key)
                
        results["duration_ms"] = (time.time() - start_time) * 1000
        
        return results


class CacheInvalidator:
    """Advanced cache invalidation system.
    
    Features:
    - Multiple invalidation strategies
    - Dependency tracking
    - Rule-based invalidation
    - Event-driven invalidation
    - Performance metrics
    - Batch processing
    """
    
    def __init__(self):
        """Initialize cache invalidator."""
        self._rules: dict[str, InvalidationRule] = {}
        self._events: list[InvalidationEvent] = []
        self._dependency_tracker = DependencyTracker()
        self._strategies: dict[InvalidationStrategy, BaseInvalidationStrategy] = {
            InvalidationStrategy.IMMEDIATE: ImmediateInvalidationStrategy(),
            InvalidationStrategy.DELAYED: DelayedInvalidationStrategy(0.0),
            InvalidationStrategy.BATCHED: BatchedInvalidationStrategy(),
        }
        self._pending_invalidations: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._is_running = False
        
        # Statistics
        self._stats = {
            "total_invalidations": 0,
            "successful_invalidations": 0,
            "failed_invalidations": 0,
            "keys_invalidated": 0,
            "avg_invalidation_time_ms": 0.0,
            "last_invalidation": None,
        }
        
    async def initialize(self) -> None:
        """Initialize cache invalidator."""
        # Start invalidation worker
        await self.start_invalidation_worker()
        
        _logger.info(
            "cache_invalidator_initialized",
            rules_count=len(self._rules),
            strategies_count=len(self._strategies),
        )
        
    async def close(self) -> None:
        """Close cache invalidator."""
        await self.stop_invalidation_worker()
        _logger.info("cache_invalidator_closed")
        
    def register_rule(self, rule: InvalidationRule) -> None:
        """Register an invalidation rule.
        
        Args:
            rule: Invalidation rule to register
        """
        self._rules[rule.name] = rule
        
        # Initialize strategy if needed
        if rule.strategy == InvalidationStrategy.DELAYED:
            self._strategies[rule.strategy] = DelayedInvalidationStrategy(rule.delay_seconds)
        elif rule.strategy == InvalidationStrategy.BATCHED:
            self._strategies[rule.strategy] = BatchedInvalidationStrategy(rule.batch_size)
            
        _logger.debug("invalidation_rule_registered", name=rule.name, strategy=rule.strategy.value)
        
    def unregister_rule(self, name: str) -> bool:
        """Unregister an invalidation rule.
        
        Args:
            name: Rule name to unregister
            
        Returns:
            True if rule was unregistered
        """
        if name in self._rules:
            del self._rules[name]
            _logger.debug("invalidation_rule_unregistered", name=name)
            return True
        return False
        
    async def invalidate(
        self,
        pattern: str,
        strategy: InvalidationStrategy = InvalidationStrategy.IMMEDIATE,
        context: dict[str, Any] | None = None,
        rule_name: str | None = None
    ) -> dict[str, Any]:
        """Invalidate cache entries matching pattern.
        
        Args:
            pattern: Key pattern to match
            strategy: Invalidation strategy
            context: Invalidation context
            rule_name: Optional rule name
            
        Returns:
            Invalidation result
        """
        context = context or {}
        
        # Get matching keys
        cache_manager = get_cache_manager()
        keys = await cache_manager._l2_cache.keys(pattern)
        
        if not keys:
            return {
                "invalidated_keys": [],
                "failed_keys": [],
                "duration_ms": 0.0,
                "message": "No keys matched pattern",
            }
            
        # Create invalidation event
        event = InvalidationEvent(
            id=str(time.time()),
            rule_name=rule_name or "manual",
            pattern=pattern,
            strategy=strategy,
            trigger=InvalidationTrigger.MANUAL,
            context=context,
        )
        
        # Execute invalidation
        strategy_instance = self._strategies.get(strategy)
        if not strategy_instance:
            raise ValueError(f"Unknown invalidation strategy: {strategy}")
            
        start_time = time.time()
        result = await strategy_instance.execute(keys, context)
        
        # Update event
        event.affected_keys = result.get("invalidated_keys", [])
        event.executed_at = datetime.now(UTC)
        event.success = len(result.get("failed_keys", [])) == 0
        event.duration_ms = result.get("duration_ms", 0.0)
        
        # Store event
        self._events.append(event)
        
        # Update statistics
        self._stats["total_invalidations"] += 1
        if event.success:
            self._stats["successful_invalidations"] += 1
        else:
            self._stats["failed_invalidations"] += 1
        self._stats["keys_invalidated"] += len(event.affected_keys)
        self._stats["last_invalidation"] = event.executed_at
        
        # Update average time
        total_time = self._stats.get("total_invalidation_time_ms", 0.0) + event.duration_ms
        self._stats["total_invalidation_time_ms"] = total_time
        self._stats["avg_invalidation_time_ms"] = total_time / self._stats["total_invalidations"]
        
        _logger.info(
            "cache_invalidated",
            pattern=pattern,
            strategy=strategy.value,
            keys_count=len(keys),
            invalidated_count=len(event.affected_keys),
            duration_ms=event.duration_ms,
        )
        
        return result
        
    async def invalidate_by_dependency(self, dependency_key: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invalidate cache entries by dependency.
        
        Args:
            dependency_key: Dependency key
            context: Invalidation context
            
        Returns:
            Invalidation result
        """
        dependents = await self._dependency_tracker.get_all_dependents(dependency_key)
        
        if not dependents:
            return {
                "invalidated_keys": [],
                "failed_keys": [],
                "duration_ms": 0.0,
                "message": "No dependents found",
            }
            
        _logger.info(
            "invalidating_by_dependency",
            dependency_key=dependency_key,
            dependents_count=len(dependents),
        )
        
        return await self.invalidate(
            pattern=",".join(dependents),  # Comma-separated for exact matches
            strategy=InvalidationStrategy.BATCHED,
            context=context or {"dependency_key": dependency_key},
            rule_name="dependency_based",
        )
        
    async def add_dependency(self, key: str, dependency: str) -> None:
        """Add cache dependency.
        
        Args:
            key: Cache key
            dependency: Dependency key
        """
        await self._dependency_tracker.add_dependency(key, dependency)
        _logger.debug("dependency_added", key=key, dependency=dependency)
        
    async def remove_dependency(self, key: str, dependency: str) -> None:
        """Remove cache dependency.
        
        Args:
            key: Cache key
            dependency: Dependency key
        """
        await self._dependency_tracker.remove_dependency(key, dependency)
        _logger.debug("dependency_removed", key=key, dependency=dependency)
        
    async def trigger_rule(self, rule_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Trigger an invalidation rule.
        
        Args:
            rule_name: Rule name to trigger
            context: Invalidation context
            
        Returns:
            Invalidation result
        """
        if rule_name not in self._rules:
            raise ValueError(f"Rule not found: {rule_name}")
            
        rule = self._rules[rule_name]
        context = context or {}
        
        # Check if rule should trigger
        if not rule.should_trigger(context):
            return {
                "invalidated_keys": [],
                "failed_keys": [],
                "duration_ms": 0.0,
                "message": "Rule conditions not met",
            }
            
        # Update rule statistics
        rule.trigger_count += 1
        rule.last_triggered = datetime.now(UTC)
        
        # Execute invalidation
        result = await self.invalidate(
            pattern=rule.pattern,
            strategy=rule.strategy,
            context=context,
            rule_name=rule_name,
        )
        
        # Update rule invalidation count
        rule.invalidation_count += len(result.get("invalidated_keys", []))
        
        # Handle cascade rules
        if rule.cascade_rules:
            for cascade_rule_name in rule.cascade_rules:
                try:
                    await self.trigger_rule(cascade_rule_name, context)
                except Exception as e:
                    _logger.error(
                        "cascade_rule_failed",
                        rule=rule_name,
                        cascade_rule=cascade_rule_name,
                        error=str(e),
                    )
                    
        return result
        
    async def start_invalidation_worker(self) -> None:
        """Start background invalidation worker."""
        if self._is_running:
            return
            
        self._is_running = True
        self._worker_task = asyncio.create_task(self._invalidation_worker())
        
        _logger.info("invalidation_worker_started")
        
    async def stop_invalidation_worker(self) -> None:
        """Stop background invalidation worker."""
        if not self._is_running:
            return
            
        self._is_running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
                
        _logger.info("invalidation_worker_stopped")
        
    async def _invalidation_worker(self) -> None:
        """Background invalidation worker."""
        while self._is_running:
            try:
                # Get next invalidation task
                try:
                    task = await asyncio.wait_for(self._pending_invalidations.get(), timeout=1.0)
                except TimeoutError:
                    continue
                    
                # Execute invalidation task
                await self.invalidate(
                    pattern=task["pattern"],
                    strategy=task["strategy"],
                    context=task.get("context", {}),
                    rule_name=task.get("rule_name"),
                )
                
                self._pending_invalidations.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("invalidation_worker_error", error=str(e))
                await asyncio.sleep(1)
                
    def get_stats(self) -> dict[str, Any]:
        """Get invalidation statistics.
        
        Returns:
            Invalidation statistics
        """
        stats = self._stats.copy()
        
        # Add rule statistics
        rule_stats = []
        for rule in self._rules.values():
            rule_stats.append({
                "name": rule.name,
                "pattern": rule.pattern,
                "strategy": rule.strategy.value,
                "trigger": rule.trigger.value,
                "enabled": rule.enabled,
                "trigger_count": rule.trigger_count,
                "invalidation_count": rule.invalidation_count,
                "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
            })
            
        stats["rules"] = rule_stats
        
        # Add recent events
        recent_events = []
        for event in self._events[-10:]:  # Last 10 events
            recent_events.append({
                "id": event.id,
                "rule_name": event.rule_name,
                "pattern": event.pattern,
                "strategy": event.strategy.value,
                "trigger": event.trigger.value,
                "created_at": event.created_at.isoformat(),
                "executed_at": event.executed_at.isoformat() if event.executed_at else None,
                "affected_keys_count": len(event.affected_keys),
                "success": event.success,
                "duration_ms": event.duration_ms,
            })
            
        stats["recent_events"] = recent_events
        
        return stats


# Global cache invalidator instance
_cache_invalidator: CacheInvalidator | None = None


def get_cache_invalidator() -> CacheInvalidator:
    """Get global cache invalidator instance.
    
    Returns:
        CacheInvalidator instance
    """
    global _cache_invalidator
    if _cache_invalidator is None:
        _cache_invalidator = CacheInvalidator()
    return _cache_invalidator
