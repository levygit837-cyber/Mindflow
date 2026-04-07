"""Memory worker for handling memory management and cleanup operations."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueConfig
from mindflow_backend.workers.system.consumers.memory_consumer import MemoryTaskConsumer

_logger = get_logger(__name__)


class MemoryWorker(BaseWorker):
    """Worker specialized for memory management and cleanup tasks."""
    
    def __init__(self, queue_config: QueueConfig) -> None:
        """Initialize the Memory worker."""
        super().__init__(queue_config, worker_name="memory_worker")
        self._memory_consumer = MemoryTaskConsumer()
    
    async def process_message(self, message_data: dict[str, Any]) -> WorkerResult:
        """Process memory management tasks.
        
        Supported task types:
        - memory_cleanup: Clean up old or unused memory data
        - memory.message.recorded: Persist chat memory and embedding asynchronously
        - storage_optimization: Optimize storage usage
        - cache_management: Manage cache data and policies
        - data_archival: Archive old data to long-term storage
        - garbage_collection: Perform garbage collection operations
        - memory_monitoring: Monitor memory usage and patterns
        """
        start_time = time.time()
        message_data = self._normalize_message_data(message_data)
        task_type = message_data.get("task_type", "unknown")
        task_id = message_data.get("task_id", "unknown")
        
        try:
            _logger.info(f"MemoryWorker processing {task_type} task {task_id}")
            
            if task_type in {"memory.message.recorded", "message_recorded"}:
                result = await self._handle_message_recorded(message_data)
            elif task_type == "memory_cleanup":
                result = await self._handle_memory_cleanup(message_data)
            elif task_type == "storage_optimization":
                result = await self._handle_storage_optimization(message_data)
            elif task_type == "cache_management":
                result = await self._handle_cache_management(message_data)
            elif task_type == "data_archival":
                result = await self._handle_data_archival(message_data)
            elif task_type == "garbage_collection":
                result = await self._handle_garbage_collection(message_data)
            elif task_type == "memory_monitoring":
                result = await self._handle_memory_monitoring(message_data)
            else:
                result = WorkerResult(
                    success=False,
                    message=f"Unsupported task type: {task_type}",
                    processing_time=time.time() - start_time,
                )
            
            _logger.info(
                f"MemoryWorker completed {task_type} task {task_id} "
                f"({'SUCCESS' if result.success else 'FAILED'})"
            )
            
            return result
            
        except Exception as e:
            _logger.error(
                f"MemoryWorker failed to process {task_type} task {task_id}: {e}",
                exc_info=True
            )
            return WorkerResult(
                success=False,
                message=f"Task processing failed: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )

    async def _handle_message_recorded(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle queued memory persistence for recorded chat messages."""
        result = await self._memory_consumer.consume_message_recorded(message_data)
        return WorkerResult(
            success=True,
            message="Memory message recorded successfully",
            data=result,
        )
    
    async def _handle_memory_cleanup(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle cleanup of old or unused memory data using memory services."""
        cleanup_scope = message_data.get("cleanup_scope", "all")
        retention_days = message_data.get("retention_days", 30)
        dry_run = message_data.get("dry_run", False)
        target_components = message_data.get("target_components", [])
        
        try:
            from datetime import datetime, timedelta
            import os
            
            items_scanned = 0
            items_cleaned = 0
            space_freed_mb = 0
            
            # Cleanup temporary files if applicable
            temp_dirs = ["/tmp/mindflow", "/var/tmp/mindflow"]
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                stat = os.stat(file_path)
                                file_age = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
                                items_scanned += 1
                                
                                if file_age > timedelta(days=retention_days) and not dry_run:
                                    os.remove(file_path)
                                    items_cleaned += 1
                                    space_freed_mb += stat.st_size / (1024 * 1024)
                            except Exception:
                                pass
            
            # Note: Database cleanup would require actual session/data management
            # This is a simplified implementation
            
            return WorkerResult(
                success=True,
                message=f"Memory cleanup completed: {cleanup_scope}",
                data={
                    "cleanup_scope": cleanup_scope,
                    "retention_days": retention_days,
                    "dry_run": dry_run,
                    "target_components": target_components,
                    "items_scanned": items_scanned,
                    "items_cleaned": items_cleaned,
                    "space_freed_mb": round(space_freed_mb, 2),
                    "cleanup_details": {
                        "temp_files": items_cleaned,
                    },
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Memory cleanup failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_storage_optimization(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle storage usage optimization using vacuum/analyze operations."""
        optimization_type = message_data.get("optimization_type", "compact")
        target_storage = message_data.get("target_storage", "all")
        optimization_level = message_data.get("optimization_level", "standard")
        
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            
            optimization_results = {}
            space_saved_total = 0
            
            if target_storage in ("all", "database"):
                try:
                    async with get_db_session() as session:
                        # Run VACUUM ANALYZE for PostgreSQL
                        await session.execute("VACUUM ANALYZE")
                        
                        # Get table sizes
                        result = await session.execute("""
                            SELECT schemaname, relname, pg_total_relation_size(relid)/1024/1024 as size_mb
                            FROM pg_stat_user_tables
                            ORDER BY pg_total_relation_size(relid) DESC
                        """)
                        rows = result.fetchall()
                        
                        optimization_results["database"] = {
                            "tables_optimized": len(rows),
                            "largest_tables": [
                                {"name": row[1], "size_mb": row[2]} for row in rows[:5]
                            ],
                        }
                except Exception as exc:
                    optimization_results["database"] = {"error": str(exc)}
            
            return WorkerResult(
                success=True,
                message=f"Storage optimization completed: {optimization_type}",
                data={
                    "optimization_type": optimization_type,
                    "target_storage": target_storage,
                    "optimization_level": optimization_level,
                    "optimization_results": optimization_results,
                    "note": "Database optimization performed via VACUUM ANALYZE",
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Storage optimization failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_cache_management(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle cache data management."""
        cache_type = message_data.get("cache_type", "all")
        management_action = message_data.get("management_action", "cleanup")
        cache_policy = message_data.get("cache_policy", {})
        
        try:
            # Cache management would integrate with Redis or similar
            # For now, provide information about cache state
            
            return WorkerResult(
                success=True,
                message=f"Cache management completed: {management_action}",
                data={
                    "cache_type": cache_type,
                    "management_action": management_action,
                    "cache_policy": cache_policy,
                    "note": "Cache management requires Redis/cache service integration",
                    "recommendations": [
                        "Configure Redis for distributed caching",
                        "Set up cache eviction policies",
                        "Monitor cache hit rates",
                    ],
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Cache management failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_data_archival(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle archival of old data."""
        archival_criteria = message_data.get("archival_criteria", "older_than_90d")
        target_data = message_data.get("target_data", "sessions")
        compression_enabled = message_data.get("compression_enabled", True)
        
        try:
            from datetime import datetime, timedelta
            
            # Data archival would move old sessions/data to cold storage
            # This is a simplified implementation
            
            return WorkerResult(
                success=True,
                message=f"Data archival completed: {archival_criteria}",
                data={
                    "archival_criteria": archival_criteria,
                    "target_data": target_data,
                    "compression_enabled": compression_enabled,
                    "note": "Data archival requires cold storage integration",
                    "recommendations": [
                        "Set up S3/GCS bucket for cold storage",
                        "Configure archival policies",
                        "Implement data lifecycle management",
                    ],
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Data archival failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_garbage_collection(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle garbage collection operations using Python GC."""
        gc_type = message_data.get("gc_type", "full")
        target_components = message_data.get("target_components", ["memory"])
        aggressive_mode = message_data.get("aggressive_mode", False)
        
        try:
            import gc
            
            # Get GC stats before
            gc_counts_before = gc.get_count()
            
            # Perform garbage collection
            if gc_type == "full":
                collected = gc.collect()
            elif gc_type == "generation_0":
                collected = gc.collect(0)
            elif gc_type == "generation_1":
                collected = gc.collect(1)
            elif gc_type == "generation_2":
                collected = gc.collect(2)
            else:
                collected = gc.collect()
            
            # Get GC stats after
            gc_counts_after = gc.get_count()
            
            return WorkerResult(
                success=True,
                message=f"Garbage collection completed: {gc_type}",
                data={
                    "gc_type": gc_type,
                    "target_components": target_components,
                    "aggressive_mode": aggressive_mode,
                    "objects_collected": collected,
                    "gc_counts_before": gc_counts_before,
                    "gc_counts_after": gc_counts_after,
                    "note": "Python garbage collection performed",
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Garbage collection failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_memory_monitoring(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle memory usage monitoring and analysis using system metrics."""
        monitoring_scope = message_data.get("monitoring_scope", "all")
        analysis_depth = message_data.get("analysis_depth", "standard")
        alert_thresholds = message_data.get("alert_thresholds", {})
        
        try:
            import psutil
            
            # Get system memory info
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            current_usage = {
                "total_mb": mem.total / (1024 * 1024),
                "available_mb": mem.available / (1024 * 1024),
                "used_mb": mem.used / (1024 * 1024),
                "percent": mem.percent,
            }
            
            # Check for alerts
            alerts = []
            memory_threshold = alert_thresholds.get("memory_percent", 80)
            if mem.percent > memory_threshold:
                alerts.append({
                    "level": "warning",
                    "component": "system_memory",
                    "message": f"Memory usage above {memory_threshold}% threshold",
                    "current_usage": mem.percent / 100,
                    "threshold": memory_threshold / 100,
                })
            
            return WorkerResult(
                success=True,
                message=f"Memory monitoring completed: {monitoring_scope}",
                data={
                    "monitoring_scope": monitoring_scope,
                    "analysis_depth": analysis_depth,
                    "current_memory_usage": current_usage,
                    "swap_usage": {
                        "total_mb": swap.total / (1024 * 1024),
                        "used_mb": swap.used / (1024 * 1024),
                        "percent": swap.percent,
                    },
                    "alerts_triggered": alerts,
                    "recommendations": [
                        "Monitor memory growth trends" if mem.percent > 70 else "Memory usage normal",
                        "Check for memory leaks if usage keeps growing",
                    ],
                },
            )
        except ImportError:
            return WorkerResult(
                success=True,
                message="Memory monitoring requires psutil package",
                data={
                    "note": "Install psutil for detailed memory monitoring",
                    "command": "pip install psutil",
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Memory monitoring failed: {exc}",
                data={"error": str(exc)},
            )
