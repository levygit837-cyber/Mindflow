"""Worker factory for creating and managing worker instances."""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.agents.analyst_worker import AnalystWorker
from mindflow_backend.workers.agents.coder_worker import CoderWorker
from mindflow_backend.workers.agents.orchestrator_worker import OrchestratorWorker
from mindflow_backend.workers.agents.researcher_worker import ResearcherWorker
from mindflow_backend.workers.base.worker import BaseWorker
from mindflow_backend.workers.config.queues import QueueConfig, QueueDefinitions
from mindflow_backend.workers.system.health_worker import HealthWorker
from mindflow_backend.workers.system.memory_worker import MemoryWorker
from mindflow_backend.workers.system.session_review_worker import SessionReviewWorker
from mindflow_backend.workers.system.vector_worker import VectorWorker

_logger = get_logger(__name__)


class WorkerFactory:
    """Factory for creating and managing worker instances."""
    
    # Registry of available worker classes
    _worker_registry: dict[str, type[BaseWorker]] = {
        # Agent workers
        "coder": CoderWorker,
        "analyst": AnalystWorker,
        "researcher": ResearcherWorker,
        "orchestrator": OrchestratorWorker,
        "browser": ResearcherWorker,
        "content": ResearcherWorker,
        
        # System workers
        "vector": VectorWorker,
        "memory": MemoryWorker,
        "session_review": SessionReviewWorker,
        "health": HealthWorker,
    }
    
    def __init__(self) -> None:
        """Initialize the worker factory."""
        self._active_workers: dict[str, BaseWorker] = {}
        self._worker_configs: dict[str, QueueConfig] = {}
        
        # Load queue configurations
        self._load_queue_configs()
        self._validate_queue_bindings()
    
    def _load_queue_configs(self) -> None:
        """Load queue configurations for all workers."""
        for queue_config in QueueDefinitions._ALL_QUEUES:
            self._worker_configs[queue_config.name] = queue_config

    def _validate_queue_bindings(self) -> None:
        """Fail fast when a queue publishes to an unregistered worker type."""
        missing = sorted(
            {
                queue_config.worker_type
                for queue_config in self._worker_configs.values()
                if queue_config.worker_type not in self._worker_registry
            }
        )
        if missing:
            raise ValueError(
                f"Queue configurations reference worker types without consumers: {', '.join(missing)}"
            )
    
    def create_worker(
        self,
        worker_type: str,
        queue_name: str | None = None,
        **kwargs: Any,
    ) -> BaseWorker:
        """Create a worker instance.
        
        Args:
            worker_type: Type of worker to create
            queue_name: Optional queue name (auto-determined if not provided)
            **kwargs: Additional arguments for worker initialization
            
        Returns:
            Created worker instance
            
        Raises:
            ValueError: If worker type is not supported
        """
        if worker_type not in self._worker_registry:
            raise ValueError(f"Unsupported worker type: {worker_type}")
        
        # Determine queue configuration
        if queue_name is None:
            queue_name = self._get_default_queue_for_worker(worker_type)
        
        if queue_name not in self._worker_configs:
            raise ValueError(f"Queue configuration not found: {queue_name}")
        
        queue_config = self._worker_configs[queue_name]
        worker_class = self._worker_registry[worker_type]
        
        # Create worker instance
        worker = worker_class(queue_config, **kwargs)
        
        # Store in active workers
        worker_key = f"{worker_type}_{queue_name}"
        self._active_workers[worker_key] = worker
        
        _logger.info(f"Created {worker_type} worker for queue {queue_name}")
        return worker
    
    def _get_default_queue_for_worker(self, worker_type: str) -> str:
        """Get the default queue name for a worker type."""
        # Map worker types to their default queue configurations
        default_mappings = {
            "coder": "coder_high",
            "analyst": "analyst_high",
            "researcher": "researcher_high",
            "browser": "browser_high",
            "content": "content_medium",
            "orchestrator": "orchestrator_critical",
            "vector": "vector_medium",
            "memory": "memory_low",
            "session_review": "session_review_high",
            "health": "health_low",
        }
        
        return default_mappings.get(worker_type, f"{worker_type}_high")
    
    def get_worker(self, worker_type: str, queue_name: str | None = None) -> BaseWorker | None:
        """Get an existing worker instance.
        
        Args:
            worker_type: Type of worker
            queue_name: Optional queue name
            
        Returns:
            Worker instance if found, None otherwise
        """
        if queue_name is None:
            queue_name = self._get_default_queue_for_worker(worker_type)
        
        worker_key = f"{worker_type}_{queue_name}"
        return self._active_workers.get(worker_key)
    
    def create_multiple_workers(
        self,
        worker_configs: list[dict[str, Any]],
    ) -> list[BaseWorker]:
        """Create multiple workers from configuration.
        
        Args:
            worker_configs: List of worker configuration dictionaries
            
        Returns:
            List of created worker instances
        """
        workers = []
        
        for config in worker_configs:
            try:
                worker = self.create_worker(**config)
                workers.append(worker)
            except Exception as e:
                _logger.error(f"Failed to create worker from config {config}: {e}")
        
        return workers
    
    def get_active_workers(self) -> dict[str, BaseWorker]:
        """Get all active worker instances."""
        return self._active_workers.copy()
    
    def remove_worker(self, worker_type: str, queue_name: str | None = None) -> bool:
        """Remove a worker from active workers.
        
        Args:
            worker_type: Type of worker to remove
            queue_name: Optional queue name
            
        Returns:
            True if worker was removed, False if not found
        """
        if queue_name is None:
            queue_name = self._get_default_queue_for_worker(worker_type)
        
        worker_key = f"{worker_type}_{queue_name}"
        
        if worker_key in self._active_workers:
            del self._active_workers[worker_key]
            _logger.info(f"Removed {worker_type} worker for queue {queue_name}")
            return True
        
        return False
    
    def get_supported_worker_types(self) -> list[str]:
        """Get list of supported worker types."""
        return list(self._worker_registry.keys())
    
    def get_queue_config(self, queue_name: str) -> QueueConfig | None:
        """Get queue configuration by name."""
        return self._worker_configs.get(queue_name)
    
    def get_all_queue_configs(self) -> dict[str, QueueConfig]:
        """Get all queue configurations."""
        return self._worker_configs.copy()
    
    def register_worker_class(
        self,
        worker_type: str,
        worker_class: type[BaseWorker],
    ) -> None:
        """Register a new worker class.
        
        Args:
            worker_type: Type identifier for the worker
            worker_class: Worker class to register
        """
        self._worker_registry[worker_type] = worker_class
        _logger.info(f"Registered worker class for type: {worker_type}")
    
    def create_worker_pool(
        self,
        worker_type: str,
        pool_size: int,
        queue_name: str | None = None,
    ) -> list[BaseWorker]:
        """Create a pool of workers of the same type.
        
        Args:
            worker_type: Type of workers to create
            pool_size: Number of workers to create
            queue_name: Optional queue name
            
        Returns:
            List of created worker instances
        """
        workers = []
        
        for i in range(pool_size):
            try:
                worker = self.create_worker(
                    worker_type=worker_type,
                    queue_name=queue_name,
                    worker_name=f"{worker_type}_worker_{i}",
                )
                workers.append(worker)
            except Exception as e:
                _logger.error(f"Failed to create worker {i} of type {worker_type}: {e}")
        
        _logger.info(f"Created pool of {len(workers)} {worker_type} workers")
        return workers
    
    async def start_all_workers(self) -> None:
        """Start all active workers."""
        for worker_key, worker in self._active_workers.items():
            try:
                await worker.start()
                _logger.info(f"Started worker: {worker_key}")
            except Exception as e:
                _logger.error(f"Failed to start worker {worker_key}: {e}")
    
    async def stop_all_workers(self) -> None:
        """Stop all active workers."""
        for worker_key, worker in self._active_workers.items():
            try:
                await worker.stop()
                _logger.info(f"Stopped worker: {worker_key}")
            except Exception as e:
                _logger.error(f"Failed to stop worker {worker_key}: {e}")
    
    def get_worker_statistics(self) -> dict[str, Any]:
        """Get statistics about active workers."""
        stats = {
            "total_workers": len(self._active_workers),
            "worker_types": {},
            "queue_distribution": {},
            "status_distribution": {
                "idle": 0,
                "processing": 0,
                "error": 0,
                "stopped": 0,
            },
        }
        
        for worker_key, worker in self._active_workers.items():
            # Count by worker type
            worker_type = worker_key.split("_")[0]
            if worker_type not in stats["worker_types"]:
                stats["worker_types"][worker_type] = 0
            stats["worker_types"][worker_type] += 1
            
            # Count by queue
            queue_name = worker.queue_config.get_full_queue_name()
            if queue_name not in stats["queue_distribution"]:
                stats["queue_distribution"][queue_name] = 0
            stats["queue_distribution"][queue_name] += 1
            
            # Count by status
            status = worker.get_status().value
            if status in stats["status_distribution"]:
                stats["status_distribution"][status] += 1
        
        return stats


# Global worker factory instance
_worker_factory: WorkerFactory | None = None


def get_worker_factory() -> WorkerFactory:
    """Get the global worker factory instance."""
    global _worker_factory
    if _worker_factory is None:
        _worker_factory = WorkerFactory()
    return _worker_factory
