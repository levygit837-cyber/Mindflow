"""Cache warming strategies for proactive cache population.

Provides intelligent cache warming with various strategies,
data sources, and performance optimization.
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from mindflow_backend.infra.cache.cache_manager import get_cache_manager
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class WarmingStrategy(Enum):
    """Cache warming strategies."""
    ON_DEMAND = "on_demand"          # Warm when first accessed
    SCHEDULED = "scheduled"          # Warm on schedule
    EVENT_DRIVEN = "event_driven"    # Warm on events
    PRECOMPUTE = "precompute"        # Pre-compute and warm
    HYBRID = "hybrid"                # Combination of strategies


class WarmingPriority(Enum):
    """Cache warming priorities."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WarmingTask:
    """Cache warming task definition."""
    name: str
    key: str
    data_loader: Callable[[], Any]
    priority: WarmingPriority = WarmingPriority.MEDIUM
    ttl: int | None = None
    tags: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    last_warmed: datetime | None = None
    warm_count: int = 0
    error_count: int = 0
    last_error: str | None = None
    estimated_size_bytes: int = 0
    
    @property
    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return self.retry_count < self.max_retries
        
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total_attempts = self.warm_count + self.error_count
        return self.warm_count / max(total_attempts, 1)


@dataclass
class WarmingSchedule:
    """Cache warming schedule definition."""
    name: str
    cron_expression: str
    tasks: list[str] = field(default_factory=list)
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
    run_count: int = 0
    
    def calculate_next_run(self) -> datetime:
        """Calculate next run time based on cron expression."""
        # Simplified cron calculation - in production, use a proper cron library
        from datetime import datetime
        
        # For now, run every hour
        now = datetime.now(UTC)
        next_run = now + timedelta(hours=1)
        return next_run.replace(minute=0, second=0, microsecond=0)


class DataSource(ABC):
    """Abstract base class for data sources."""
    
    @abstractmethod
    async def load_data(self, key: str) -> Any:
        """Load data for the given key."""
        pass
        
    @abstractmethod
    async def get_available_keys(self) -> list[str]:
        """Get list of available keys."""
        pass
        
    @abstractmethod
    async def estimate_size(self, key: str) -> int:
        """Estimate size of data for key."""
        pass


class DatabaseDataSource(DataSource):
    """Database data source for cache warming."""
    
    def __init__(self, query_loader: Callable[[str], str]):
        """Initialize database data source.
        
        Args:
            query_loader: Function that returns SQL query for key
        """
        self.query_loader = query_loader
        
    async def load_data(self, key: str) -> Any:
        """Load data from database."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            
            query = self.query_loader(key)
            async with get_db_session() as session:
                result = await session.execute(query)
                data = result.fetchall()
                return [dict(row) for row in data]
                
        except Exception as e:
            _logger.error("database_data_source_load_failed", key=key, error=str(e))
            raise
            
    async def get_available_keys(self) -> list[str]:
        """Get available keys from database."""
        # This would be implemented based on specific database schema
        return []
        
    async def estimate_size(self, key: str) -> int:
        """Estimate size of database data."""
        try:
            data = await self.load_data(key)
            return len(json.dumps(data).encode('utf-8'))
        except Exception:
            return 1024


class APIDataSource(DataSource):
    """API data source for cache warming."""
    
    def __init__(self, api_client: Callable[[str], Any]):
        """Initialize API data source.
        
        Args:
            api_client: Function that calls API for key
        """
        self.api_client = api_client
        
    async def load_data(self, key: str) -> Any:
        """Load data from API."""
        try:
            data = await self.api_client(key)
            return data
        except Exception as e:
            _logger.error("api_data_source_load_failed", key=key, error=str(e))
            raise
            
    async def get_available_keys(self) -> list[str]:
        """Get available keys from API."""
        # This would be implemented based on specific API
        return []
        
    async def estimate_size(self, key: str) -> int:
        """Estimate size of API data."""
        try:
            data = await self.load_data(key)
            return len(json.dumps(data).encode('utf-8'))
        except Exception:
            return 1024


class CacheWarmer:
    """Advanced cache warming system.
    
    Features:
    - Multiple warming strategies
    - Scheduled warming
    - Dependency resolution
    - Performance metrics
    - Error handling and retry
    - Resource management
    """
    
    def __init__(self):
        """Initialize cache warmer."""
        self._tasks: dict[str, WarmingTask] = {}
        self._schedules: dict[str, WarmingSchedule] = {}
        self._data_sources: dict[str, DataSource] = {}
        self._warming_queue: asyncio.Queue = asyncio.Queue()
        self._worker_tasks: list[asyncio.Task] = []
        self._is_running = False
        self._max_workers = 5
        self._warming_interval = 300  # 5 minutes
        self._scheduler_task: asyncio.Task | None = None
        
        # Statistics
        self._stats = {
            "total_warms": 0,
            "successful_warms": 0,
            "failed_warms": 0,
            "total_data_size_mb": 0.0,
            "warming_time_ms": 0.0,
            "avg_warming_time_ms": 0.0,
            "last_warm_time": None,
        }
        
    async def initialize(self) -> None:
        """Initialize cache warmer."""
        # Start warming workers
        await self.start_warming_workers()
        
        # Start scheduler
        await self.start_scheduler()
        
        _logger.info(
            "cache_warmer_initialized",
            tasks_count=len(self._tasks),
            schedules_count=len(self._schedules),
            max_workers=self._max_workers,
        )
        
    async def close(self) -> None:
        """Close cache warmer."""
        await self.stop_scheduler()
        await self.stop_warming_workers()
        _logger.info("cache_warmer_closed")
        
    def register_task(self, task: WarmingTask) -> None:
        """Register a warming task.
        
        Args:
            task: Warming task to register
        """
        self._tasks[task.name] = task
        _logger.debug("warming_task_registered", name=task.name, priority=task.priority.value)
        
    def unregister_task(self, name: str) -> bool:
        """Unregister a warming task.
        
        Args:
            name: Task name to unregister
            
        Returns:
            True if task was unregistered
        """
        if name in self._tasks:
            del self._tasks[name]
            _logger.debug("warming_task_unregistered", name=name)
            return True
        return False
        
    def register_schedule(self, schedule: WarmingSchedule) -> None:
        """Register a warming schedule.
        
        Args:
            schedule: Warming schedule to register
        """
        self._schedules[schedule.name] = schedule
        schedule.next_run = schedule.calculate_next_run()
        _logger.debug("warming_schedule_registered", name=schedule.name)
        
    def register_data_source(self, name: str, data_source: DataSource) -> None:
        """Register a data source.
        
        Args:
            name: Data source name
            data_source: Data source instance
        """
        self._data_sources[name] = data_source
        _logger.debug("data_source_registered", name=name)
        
    async def warm_cache(self, task_names: list[str] | None = None) -> dict[str, Any]:
        """Warm cache for specified tasks.
        
        Args:
            task_names: List of task names to warm (all if None)
            
        Returns:
            Warming results
        """
        if task_names is None:
            tasks_to_warm = list(self._tasks.values())
        else:
            tasks_to_warm = [self._tasks[name] for name in task_names if name in self._tasks]
            
        # Sort by priority
        tasks_to_warm.sort(key=lambda t: t.priority.value, reverse=True)
        
        start_time = time.time()
        results = {
            "total_tasks": len(tasks_to_warm),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_size_mb": 0.0,
            "duration_ms": 0.0,
            "task_results": {},
        }
        
        for task in tasks_to_warm:
            try:
                task_result = await self._warm_task(task)
                results["task_results"][task.name] = task_result
                
                if task_result["success"]:
                    results["successful"] += 1
                    results["total_size_mb"] += task_result["size_mb"]
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                _logger.error("warming_task_failed", task=task.name, error=str(e))
                results["failed"] += 1
                results["task_results"][task.name] = {
                    "success": False,
                    "error": str(e),
                }
                
        results["duration_ms"] = (time.time() - start_time) * 1000
        
        # Update statistics
        self._stats["total_warms"] += results["total_tasks"]
        self._stats["successful_warms"] += results["successful"]
        self._stats["failed_warms"] += results["failed"]
        self._stats["total_data_size_mb"] += results["total_size_mb"]
        self._stats["warming_time_ms"] += results["duration_ms"]
        self._stats["avg_warming_time_ms"] = (
            self._stats["warming_time_ms"] / max(self._stats["total_warms"], 1)
        )
        self._stats["last_warm_time"] = datetime.now(UTC)
        
        _logger.info(
            "cache_warming_completed",
            **{k: v for k, v in results.items() if k != "task_results"}
        )
        
        return results
        
    async def _warm_task(self, task: WarmingTask) -> dict[str, Any]:
        """Warm a single task.
        
        Args:
            task: Task to warm
            
        Returns:
            Task warming result
        """
        start_time = time.time()
        
        try:
            # Check dependencies
            for dep_name in task.dependencies:
                if dep_name in self._tasks:
                    dep_task = self._tasks[dep_name]
                    if dep_task.last_warmed is None:
                        _logger.warning(
                            "warming_task_dependency_not_warmed",
                            task=task.name,
                            dependency=dep_name,
                        )
                        
            # Load data
            data = await task.data_loader()
            
            # Estimate size
            if task.estimated_size_bytes == 0:
                task.estimated_size_bytes = len(json.dumps(data).encode('utf-8'))
                
            # Store in cache
            cache_manager = get_cache_manager()
            success = await cache_manager.set(
                key=task.key,
                value=data,
                ttl=task.ttl,
                tags=task.tags,
            )
            
            if success:
                task.warm_count += 1
                task.last_warmed = datetime.now(UTC)
                task.retry_count = 0  # Reset retry count on success
                
                result = {
                    "success": True,
                    "size_mb": task.estimated_size_bytes / (1024 * 1024),
                    "duration_ms": (time.time() - start_time) * 1000,
                    "warm_count": task.warm_count,
                }
                
                _logger.debug(
                    "warming_task_success",
                    task=task.name,
                    key=task.key,
                    size_mb=result["size_mb"],
                )
                
                return result
            else:
                raise RuntimeError("Failed to store in cache")
                
        except Exception as e:
            task.error_count += 1
            task.retry_count += 1
            task.last_error = str(e)
            
            result = {
                "success": False,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000,
                "retry_count": task.retry_count,
                "error_count": task.error_count,
            }
            
            _logger.warning(
                "warming_task_failed",
                task=task.name,
                error=str(e),
                retry_count=task.retry_count,
            )
            
            return result
            
    async def warm_on_demand(self, key: str, data_loader: Callable[[], Any], **kwargs) -> bool:
        """Warm cache on demand for a specific key.
        
        Args:
            key: Cache key
            data_loader: Function to load data
            **kwargs: Additional cache options
            
        Returns:
            True if successful
        """
        try:
            data = await data_loader()
            cache_manager = get_cache_manager()
            
            return await cache_manager.set(key=key, value=data, **kwargs)
            
        except Exception as e:
            _logger.error("on_demand_warming_failed", key=key, error=str(e))
            return False
            
    async def start_warming_workers(self) -> None:
        """Start background warming workers."""
        if self._is_running:
            return
            
        self._is_running = True
        
        # Create worker tasks
        for i in range(self._max_workers):
            task = asyncio.create_task(self._warming_worker(f"worker-{i}"))
            self._worker_tasks.append(task)
            
        _logger.info("warming_workers_started", count=self._max_workers)
        
    async def stop_warming_workers(self) -> None:
        """Stop background warming workers."""
        if not self._is_running:
            return
            
        self._is_running = False
        
        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        
        _logger.info("warming_workers_stopped")
        
    async def start_scheduler(self) -> None:
        """Start scheduled warming."""
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        _logger.info("warming_scheduler_started")
        
    async def stop_scheduler(self) -> None:
        """Stop scheduled warming."""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
                
        _logger.info("warming_scheduler_stopped")
        
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while True:
            try:
                current_time = datetime.now(UTC)
                
                # Check for due schedules
                for schedule in self._schedules.values():
                    if (schedule.enabled and 
                        schedule.next_run and 
                        current_time >= schedule.next_run):
                        
                        await self._run_schedule(schedule)
                        schedule.last_run = current_time
                        schedule.next_run = schedule.calculate_next_run()
                        schedule.run_count += 1
                        
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("warming_scheduler_loop_error", error=str(e))
                await asyncio.sleep(60)
                
    async def _run_schedule(self, schedule: WarmingSchedule) -> None:
        """Run a warming schedule.
        
        Args:
            schedule: Schedule to run
        """
        _logger.info("running_warming_schedule", name=schedule.name)
        
        task_names = [task_name for task_name in schedule.tasks if task_name in self._tasks]
        
        if task_names:
            await self.warm_cache(task_names)
        else:
            _logger.warning("no_valid_tasks_in_schedule", name=schedule.name)
            
    async def _warming_worker(self, worker_name: str) -> None:
        """Background warming worker.
        
        Args:
            worker_name: Worker identifier
        """
        _logger.debug("warming_worker_started", worker=worker_name)
        
        while self._is_running:
            try:
                # Get next task from queue (with timeout)
                try:
                    task = await asyncio.wait_for(self._warming_queue.get(), timeout=1.0)
                except TimeoutError:
                    continue
                    
                await self._warm_task(task)
                self._warming_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("warming_worker_error", worker=worker_name, error=str(e))
                await asyncio.sleep(1)
                
        _logger.debug("warming_worker_stopped", worker=worker_name)
        
    def get_stats(self) -> dict[str, Any]:
        """Get warming statistics.
        
        Returns:
            Warming statistics
        """
        stats = self._stats.copy()
        
        # Add task statistics
        task_stats = []
        for task in self._tasks.values():
            task_stats.append({
                "name": task.name,
                "key": task.key,
                "priority": task.priority.value,
                "warm_count": task.warm_count,
                "error_count": task.error_count,
                "success_rate": task.success_rate,
                "last_warmed": task.last_warmed.isoformat() if task.last_warmed else None,
                "estimated_size_mb": task.estimated_size_bytes / (1024 * 1024),
            })
            
        stats["tasks"] = task_stats
        
        # Add schedule statistics
        schedule_stats = []
        for schedule in self._schedules.values():
            schedule_stats.append({
                "name": schedule.name,
                "enabled": schedule.enabled,
                "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
                "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
                "run_count": schedule.run_count,
                "tasks_count": len(schedule.tasks),
            })
            
        stats["schedules"] = schedule_stats
        
        return stats


# Global cache warmer instance
_cache_warmer: CacheWarmer | None = None


def get_cache_warmer() -> CacheWarmer:
    """Get global cache warmer instance.
    
    Returns:
        CacheWarmer instance
    """
    global _cache_warmer
    if _cache_warmer is None:
        _cache_warmer = CacheWarmer()
    return _cache_warmer
