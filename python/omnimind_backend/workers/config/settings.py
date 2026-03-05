"""Worker settings and configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from omnimind_backend.infra.config import get_settings


@dataclass
class WorkerSettings:
    """Settings for worker configuration."""
    
    # RabbitMQ connection
    rabbitmq_url: str
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_username: str
    rabbitmq_password: str
    rabbitmq_virtual_host: str = "/"
    
    # Worker defaults
    default_concurrency: int = 1
    default_max_retries: int = 3
    default_retry_delay: int = 60
    default_message_ttl: int = 3600
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Performance
    prefetch_count: int = 10
    heartbeat: int = 600
    connection_timeout: int = 30
    
    @classmethod
    def from_settings(cls) -> WorkerSettings:
        """Create WorkerSettings from application settings."""
        app_settings = get_settings()
        
        return cls(
            rabbitmq_url=getattr(app_settings, "rabbitmq_url", "amqp://localhost:5672/"),
            rabbitmq_host=getattr(app_settings, "rabbitmq_host", "localhost"),
            rabbitmq_port=getattr(app_settings, "rabbitmq_port", 5672),
            rabbitmq_username=getattr(app_settings, "rabbitmq_username", "guest"),
            rabbitmq_password=getattr(app_settings, "rabbitmq_password", "guest"),
            rabbitmq_virtual_host=getattr(app_settings, "rabbitmq_virtual_host", "/"),
            default_concurrency=getattr(app_settings, "worker_default_concurrency", 1),
            default_max_retries=getattr(app_settings, "worker_default_max_retries", 3),
            default_retry_delay=getattr(app_settings, "worker_default_retry_delay", 60),
            default_message_ttl=getattr(app_settings, "worker_default_message_ttl", 3600),
            enable_metrics=getattr(app_settings, "worker_enable_metrics", True),
            metrics_port=getattr(app_settings, "worker_metrics_port", 9090),
            log_level=getattr(app_settings, "worker_log_level", "INFO"),
            log_format=getattr(app_settings, "worker_log_format", "json"),
            prefetch_count=getattr(app_settings, "worker_prefetch_count", 10),
            heartbeat=getattr(app_settings, "worker_heartbeat", 600),
            connection_timeout=getattr(app_settings, "worker_connection_timeout", 30),
        )


def get_worker_settings() -> WorkerSettings:
    """Get worker settings."""
    return WorkerSettings.from_settings()
