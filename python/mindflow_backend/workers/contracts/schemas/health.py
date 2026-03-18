"""Health schemas for worker monitoring and RabbitMQ rollout observability."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkerHealthSnapshot(BaseModel):
    """Worker-level health payload for monitoring dashboards and logs."""

    model_config = ConfigDict(extra="forbid")

    worker_name: str
    worker_type: str
    queue_name: str
    status: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tasks_processed: int = Field(default=0, ge=0)
    tasks_successful: int = Field(default=0, ge=0)
    tasks_failed: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    retry_rate: float = Field(default=0.0, ge=0.0)
    average_processing_time: float = Field(default=0.0, ge=0.0)
    uptime: float = Field(default=0.0, ge=0.0)
    last_activity: float | None = None
    error_rate: float = Field(default=0.0, ge=0.0)
    success_rate: float = Field(default=0.0, ge=0.0)
    memory_usage_mb: float = Field(default=0.0, ge=0.0)
    cpu_usage: float = Field(default=0.0, ge=0.0)
    last_correlation_id: str | None = None
    is_healthy: bool = True


class QueueHealthSnapshot(BaseModel):
    """Queue-level health payload for RabbitMQ rollout observability."""

    model_config = ConfigDict(extra="forbid")

    queue_name: str
    domain: str
    worker_type: str
    priority: str
    message_count: int | None = None
    consumer_count: int | None = None
    retry_count: int = Field(default=0, ge=0)
    retry_rate: float = Field(default=0.0, ge=0.0)
    dead_letter_queue: str
    connection_status: Literal["connected", "degraded", "disconnected", "unknown"] = "unknown"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RabbitConnectionSnapshot(BaseModel):
    """Connection-level health summary for the worker subsystem."""

    model_config = ConfigDict(extra="forbid")

    connection_status: Literal["connected", "degraded", "disconnected", "unknown"] = "unknown"
    channel_status: Literal["open", "degraded", "closed", "unknown"] = "unknown"
    total_queues: int = Field(default=0, ge=0)
    connected_workers: int = Field(default=0, ge=0)
    disconnected_workers: int = Field(default=0, ge=0)


class WorkerSystemHealthReport(BaseModel):
    """Typed health report for worker/runtime startup and monitoring logs."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None
    overall_health_score: float = Field(default=0.0, ge=0.0)
    total_workers: int = Field(default=0, ge=0)
    active_workers: int = Field(default=0, ge=0)
    error_workers: int = Field(default=0, ge=0)
    system_success_rate: float = Field(default=0.0, ge=0.0)
    system_error_rate: float = Field(default=0.0, ge=0.0)
    average_processing_time: float = Field(default=0.0, ge=0.0)
    rabbitmq: RabbitConnectionSnapshot = Field(default_factory=RabbitConnectionSnapshot)
    workers: list[WorkerHealthSnapshot] = Field(default_factory=list)
    queues: dict[str, QueueHealthSnapshot] = Field(default_factory=dict)
    unhealthy_workers: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
