"""System task definitions and utilities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope
from mindflow_backend.workers.infrastructure.queue_manager import get_queue_manager
from mindflow_backend.workers.system.schemas.session_review_tasks import (
    SessionReviewRequestedPayload,
    build_session_review_idempotency_key,
)

_logger = get_logger(__name__)


@dataclass
class SystemTask:
    """Base class for system tasks."""
    
    task_type: str
    session_id: str
    system_component: str
    priority: str = "medium"
    task_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Generate task ID if not provided."""
        if "task_id" not in self.metadata:
            self.metadata["task_id"] = str(uuid.uuid4())
    
    @property
    def task_id(self) -> str:
        """Get task ID."""
        return self.metadata["task_id"]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary for queue publishing."""
        envelope = QueueMessageEnvelope(
            schema_version="1.0",
            task_id=self.task_id,
            task_type=self.task_type,
            session_id=self.session_id,
            correlation_id=self.task_id,
            idempotency_key=self.task_id,
            created_at=datetime.now(UTC),
            metadata={
                **self.metadata,
                "system_component": self.system_component,
                "priority": self.priority,
            },
            payload=self.task_data,
        )

        return envelope.model_dump(mode="json")


class SystemTaskDefinitions:
    """Definitions and utilities for system tasks."""
    
    # Session Review Tasks
    @staticmethod
    def create_session_review_requested_task(
        session_id: str,
        window_index: int,
        window_range: tuple[int, int],
        trigger_type: str,
        review_priority: str = "medium",
        tokens_in_window: int = 0,
        total_tokens_processed: int = 0,
        threshold: int = 0,
        origin: str = "session_review_service",
    ) -> SystemTask:
        """Create a queue-safe session review request with deterministic idempotency."""
        payload = SessionReviewRequestedPayload(
            session_id=session_id,
            window_index=window_index,
            window_range=window_range,
            trigger_type=trigger_type,
            priority=review_priority,
            tokens_in_window=tokens_in_window,
            total_tokens_processed=total_tokens_processed,
            threshold=threshold,
            origin=origin,
        )
        task_id = build_session_review_idempotency_key(
            session_id=session_id,
            window_index=window_index,
            trigger_type=trigger_type,
        )

        return SystemTask(
            task_type="session_review.requested",
            session_id=session_id,
            system_component="session_review",
            priority=review_priority,
            task_data=payload.model_dump(mode="json"),
            metadata={
                "task_id": task_id,
                "created_at": payload.requested_at.isoformat(),
                "estimated_duration": 120,
                "window_range": list(window_range),
                "origin": origin,
            },
        )

    @staticmethod
    def create_window_review_task(
        session_id: str,
        window_index: int = 0,
        trigger_type: str = "token_limit",
        review_priority: str = "medium",
    ) -> SystemTask:
        """Create a session window review task."""
        return SystemTask(
            task_type="window_review",
            session_id=session_id,
            system_component="session_review",
            priority=review_priority,
            task_data={
                "window_index": window_index,
                "trigger_type": trigger_type,
                "review_priority": review_priority,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 120,
            },
        )
    
    @staticmethod
    def create_context_summarization_task(
        session_id: str,
        context_range: str = "full_session",
        summary_type: str = "comprehensive",
        target_length: int = 500,
    ) -> SystemTask:
        """Create a context summarization task."""
        return SystemTask(
            task_type="context_summarization",
            session_id=session_id,
            system_component="session_review",
            priority="medium",
            task_data={
                "context_range": context_range,
                "summary_type": summary_type,
                "target_length": target_length,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )
    
    @staticmethod
    def create_memory_consolidation_task(
        session_id: str,
        consolidation_type: str = "incremental",
        retention_policy: str = "keep_all",
    ) -> SystemTask:
        """Create a memory consolidation task."""
        return SystemTask(
            task_type="memory_consolidation",
            session_id=session_id,
            system_component="session_review",
            priority="low",
            task_data={
                "consolidation_type": consolidation_type,
                "retention_policy": retention_policy,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 60,
            },
        )
    
    @staticmethod
    def create_token_management_task(
        session_id: str,
        action: str = "reset_window",
        new_window_size: int | None = None,
        budget_adjustment: int = 0,
    ) -> SystemTask:
        """Create a token management task."""
        return SystemTask(
            task_type="token_management",
            session_id=session_id,
            system_component="session_review",
            priority="medium",
            task_data={
                "action": action,
                "new_window_size": new_window_size,
                "budget_adjustment": budget_adjustment,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 30,
            },
        )
    
    @staticmethod
    def create_session_cleanup_task(
        session_id: str,
        cleanup_criteria: str = "inactive_7d",
        dry_run: bool = True,
        target_sessions: list[str] = None,
    ) -> SystemTask:
        """Create a session cleanup task."""
        return SystemTask(
            task_type="session_cleanup",
            session_id=session_id,
            system_component="session_review",
            priority="low",
            task_data={
                "cleanup_criteria": cleanup_criteria,
                "dry_run": dry_run,
                "target_sessions": target_sessions or [],
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 180,
            },
        )
    
    # Vector Store Tasks
    @staticmethod
    def create_batch_indexing_task(
        session_id: str,
        embeddings_batch: list[dict[str, Any]],
        vector_store: str = "default",
        batch_size: int = 100,
    ) -> SystemTask:
        """Create a batch vector indexing task."""
        return SystemTask(
            task_type="batch_indexing",
            session_id=session_id,
            system_component="vector",
            priority="medium",
            task_data={
                "embeddings_batch": embeddings_batch,
                "vector_store": vector_store,
                "batch_size": batch_size,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 300,
            },
        )
    
    @staticmethod
    def create_incremental_indexing_task(
        session_id: str,
        new_embeddings: list[dict[str, Any]],
        update_strategy: str = "append",
    ) -> SystemTask:
        """Create an incremental vector indexing task."""
        return SystemTask(
            task_type="incremental_indexing",
            session_id=session_id,
            system_component="vector",
            priority="medium",
            task_data={
                "new_embeddings": new_embeddings,
                "update_strategy": update_strategy,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 120,
            },
        )
    
    @staticmethod
    def create_reindexing_task(
        session_id: str,
        vector_store: str = "default",
        reindex_reason: str = "maintenance",
        backup_existing: bool = True,
    ) -> SystemTask:
        """Create a full reindexing task."""
        return SystemTask(
            task_type="reindexing",
            session_id=session_id,
            system_component="vector",
            priority="low",
            task_data={
                "vector_store": vector_store,
                "reindex_reason": reindex_reason,
                "backup_existing": backup_existing,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 600,
            },
        )
    
    @staticmethod
    def create_embedding_generation_task(
        session_id: str,
        content_items: list[dict[str, Any]],
        embedding_model: str = "default",
        batch_process: bool = True,
    ) -> SystemTask:
        """Create an embedding generation task."""
        return SystemTask(
            task_type="embedding_generation",
            session_id=session_id,
            system_component="vector",
            priority="medium",
            task_data={
                "content_items": content_items,
                "embedding_model": embedding_model,
                "batch_process": batch_process,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 180,
            },
        )
    
    @staticmethod
    def create_vector_search_task(
        session_id: str,
        query_vector: list[float],
        search_params: dict[str, Any],
        result_limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> SystemTask:
        """Create a vector search task."""
        return SystemTask(
            task_type="vector_search",
            session_id=session_id,
            system_component="vector",
            priority="high",
            task_data={
                "query_vector": query_vector,
                "search_params": search_params,
                "result_limit": result_limit,
                "similarity_threshold": similarity_threshold,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 45,
            },
        )
    
    # Memory Management Tasks
    @staticmethod
    def create_memory_cleanup_task(
        session_id: str,
        cleanup_scope: str = "all",
        retention_days: int = 30,
        dry_run: bool = False,
        target_components: list[str] = None,
    ) -> SystemTask:
        """Create a memory cleanup task."""
        return SystemTask(
            task_type="memory_cleanup",
            session_id=session_id,
            system_component="memory",
            priority="low",
            task_data={
                "cleanup_scope": cleanup_scope,
                "retention_days": retention_days,
                "dry_run": dry_run,
                "target_components": target_components or [],
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 240,
            },
        )
    
    @staticmethod
    def create_storage_optimization_task(
        session_id: str,
        optimization_type: str = "compact",
        target_storage: str = "all",
        optimization_level: str = "standard",
    ) -> SystemTask:
        """Create a storage optimization task."""
        return SystemTask(
            task_type="storage_optimization",
            session_id=session_id,
            system_component="memory",
            priority="low",
            task_data={
                "optimization_type": optimization_type,
                "target_storage": target_storage,
                "optimization_level": optimization_level,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 360,
            },
        )
    
    @staticmethod
    def create_cache_management_task(
        session_id: str,
        cache_type: str = "all",
        management_action: str = "cleanup",
        cache_policy: dict[str, Any] = None,
    ) -> SystemTask:
        """Create a cache management task."""
        return SystemTask(
            task_type="cache_management",
            session_id=session_id,
            system_component="memory",
            priority="low",
            task_data={
                "cache_type": cache_type,
                "management_action": management_action,
                "cache_policy": cache_policy or {},
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 60,
            },
        )
    
    @staticmethod
    def create_data_archival_task(
        session_id: str,
        archival_criteria: str = "older_than_90d",
        target_data: str = "sessions",
        compression_enabled: bool = True,
        archive_location: str = "default",
    ) -> SystemTask:
        """Create a data archival task."""
        return SystemTask(
            task_type="data_archival",
            session_id=session_id,
            system_component="memory",
            priority="low",
            task_data={
                "archival_criteria": archival_criteria,
                "target_data": target_data,
                "compression_enabled": compression_enabled,
                "archive_location": archive_location,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 180,
            },
        )
    
    @staticmethod
    def create_garbage_collection_task(
        session_id: str,
        gc_type: str = "full",
        target_components: list[str] = None,
        aggressive_mode: bool = False,
    ) -> SystemTask:
        """Create a garbage collection task."""
        return SystemTask(
            task_type="garbage_collection",
            session_id=session_id,
            system_component="memory",
            priority="low",
            task_data={
                "gc_type": gc_type,
                "target_components": target_components or ["memory", "storage"],
                "aggressive_mode": aggressive_mode,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 45,
            },
        )
    
    @staticmethod
    def create_memory_monitoring_task(
        session_id: str,
        monitoring_scope: str = "all",
        analysis_depth: str = "standard",
        alert_thresholds: dict[str, Any] = None,
    ) -> SystemTask:
        """Create a memory monitoring task."""
        return SystemTask(
            task_type="memory_monitoring",
            session_id=session_id,
            system_component="memory",
            priority="low",
            task_data={
                "monitoring_scope": monitoring_scope,
                "analysis_depth": analysis_depth,
                "alert_thresholds": alert_thresholds or {},
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 30,
            },
        )
    
    # Health Monitoring Tasks
    @staticmethod
    def create_system_health_check_task(
        session_id: str,
        check_scope: str = "full",
        check_depth: str = "standard",
        include_components: list[str] = None,
    ) -> SystemTask:
        """Create a system health check task."""
        return SystemTask(
            task_type="system_health_check",
            session_id=session_id,
            system_component="health",
            priority="low",
            task_data={
                "check_scope": check_scope,
                "check_depth": check_depth,
                "include_components": include_components or [],
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 60,
            },
        )
    
    @staticmethod
    def create_component_monitoring_task(
        session_id: str,
        target_components: list[str],
        monitoring_duration: int = 300,
        metrics_collected: list[str] = None,
    ) -> SystemTask:
        """Create a component monitoring task."""
        return SystemTask(
            task_type="component_monitoring",
            session_id=session_id,
            system_component="health",
            priority="low",
            task_data={
                "target_components": target_components,
                "monitoring_duration": monitoring_duration,
                "metrics_collected": metrics_collected or ["all"],
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": monitoring_duration,
            },
        )
    
    @staticmethod
    def create_performance_metrics_task(
        session_id: str,
        metrics_type: str = "comprehensive",
        time_range: str = "1h",
        aggregation_level: str = "5m",
    ) -> SystemTask:
        """Create a performance metrics collection task."""
        return SystemTask(
            task_type="performance_metrics",
            session_id=session_id,
            system_component="health",
            priority="low",
            task_data={
                "metrics_type": metrics_type,
                "time_range": time_range,
                "aggregation_level": aggregation_level,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )
    
    @staticmethod
    def create_alert_evaluation_task(
        session_id: str,
        alert_rules: list[dict[str, Any]],
        evaluation_context: dict[str, Any],
        auto_resolve: bool = True,
    ) -> SystemTask:
        """Create an alert evaluation task."""
        return SystemTask(
            task_type="alert_evaluation",
            session_id=session_id,
            system_component="health",
            priority="medium",
            task_data={
                "alert_rules": alert_rules,
                "evaluation_context": evaluation_context,
                "auto_resolve": auto_resolve,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 30,
            },
        )
    
    @staticmethod
    def create_diagnostic_analysis_task(
        session_id: str,
        analysis_scope: str = "full",
        diagnostic_type: str = "performance",
        time_period: str = "24h",
    ) -> SystemTask:
        """Create a diagnostic analysis task."""
        return SystemTask(
            task_type="diagnostic_analysis",
            session_id=session_id,
            system_component="health",
            priority="medium",
            task_data={
                "analysis_scope": analysis_scope,
                "diagnostic_type": diagnostic_type,
                "time_period": time_period,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 120,
            },
        )
    
    @staticmethod
    def create_health_reporting_task(
        session_id: str,
        report_type: str = "summary",
        report_period: str = "daily",
        include_recommendations: bool = True,
        output_format: str = "json",
    ) -> SystemTask:
        """Create a health reporting task."""
        return SystemTask(
            task_type="health_reporting",
            session_id=session_id,
            system_component="health",
            priority="low",
            task_data={
                "report_type": report_type,
                "report_period": report_period,
                "include_recommendations": include_recommendations,
                "output_format": output_format,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 45,
            },
        )


class SystemTaskPublisher:
    """Utility class for publishing system tasks to queues."""
    
    def __init__(self) -> None:
        """Initialize the task publisher."""
        self.queue_manager = get_queue_manager()
    
    async def publish_task(self, task: SystemTask) -> bool:
        """Publish a system task to the appropriate queue.
        
        Args:
            task: System task to publish
            
        Returns:
            True if task was published successfully
        """
        # Determine queue name based on system component and priority
        queue_name = self._get_queue_name(task.system_component, task.priority)
        
        # Convert task to dictionary
        task_dict = task.to_dict()
        
        # Set message priority based on task priority
        priority = self._get_message_priority(task.priority)
        
        # Publish to queue
        success = await self.queue_manager.publish_message(
            queue_name=queue_name,
            message_data=task_dict,
            priority=priority,
        )
        
        if success:
            _logger.info(f"Published {task.task_type} task {task.task_id} to {queue_name}")
        else:
            _logger.error(f"Failed to publish task {task.task_id} to {queue_name}")
        
        return success
    
    def _get_queue_name(self, system_component: str, priority: str) -> str:
        """Get queue name for system component and priority."""
        # Map system components and priorities to queue names
        queue_mappings = {
            ("session_review", "critical"): "session_review_high",
            ("session_review", "high"): "session_review_high",
            ("session_review", "medium"): "session_review_high",
            ("session_review", "low"): "session_review_high",
            
            ("vector", "critical"): "vector_medium",
            ("vector", "high"): "vector_medium",
            ("vector", "medium"): "vector_medium",
            ("vector", "low"): "vector_medium",
            
            ("memory", "critical"): "memory_low",
            ("memory", "high"): "memory_low",
            ("memory", "medium"): "memory_low",
            ("memory", "low"): "memory_low",
            
            ("health", "critical"): "health_low",
            ("health", "high"): "health_low",
            ("health", "medium"): "health_low",
            ("health", "low"): "health_low",
        }
        
        return queue_mappings.get((system_component, priority), f"{system_component}_low")
    
    def _get_message_priority(self, task_priority: str) -> int:
        """Convert task priority to message priority."""
        priority_mapping = {
            "critical": 9,
            "high": 7,
            "medium": 5,
            "low": 3,
        }
        
        return priority_mapping.get(task_priority, 5)
    
    async def publish_multiple_tasks(self, tasks: list[SystemTask]) -> dict[str, bool]:
        """Publish multiple tasks to queues.
        
        Args:
            tasks: List of tasks to publish
            
        Returns:
            Dictionary mapping task IDs to success status
        """
        results = {}
        
        for task in tasks:
            results[task.task_id] = await self.publish_task(task)
        
        return results


# Global task publisher instance
_task_publisher: SystemTaskPublisher | None = None


def get_system_task_publisher() -> SystemTaskPublisher:
    """Get the global system task publisher instance."""
    global _task_publisher
    if _task_publisher is None:
        _task_publisher = SystemTaskPublisher()
    return _task_publisher
