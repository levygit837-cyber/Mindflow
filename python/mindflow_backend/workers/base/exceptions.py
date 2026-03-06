"""Worker-specific exceptions."""

from __future__ import annotations


class WorkerError(Exception):
    """Base exception for worker-related errors."""
    
    def __init__(
        self,
        message: str,
        worker_name: str | None = None,
        task_id: str | None = None,
        queue_name: str | None = None,
    ) -> None:
        self.worker_name = worker_name
        self.task_id = task_id
        self.queue_name = queue_name
        super().__init__(message)


class WorkerConfigurationError(WorkerError):
    """Raised when worker configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        worker_name: str | None = None,
        config_key: str | None = None,
    ) -> None:
        self.config_key = config_key
        super().__init__(message, worker_name=worker_name)


class WorkerConnectionError(WorkerError):
    """Raised when worker cannot connect to RabbitMQ or other services."""
    
    def __init__(
        self,
        message: str,
        worker_name: str | None = None,
        service: str | None = None,
    ) -> None:
        self.service = service
        super().__init__(message, worker_name=worker_name)


class WorkerProcessingError(WorkerError):
    """Raised when task processing fails."""
    
    def __init__(
        self,
        message: str,
        worker_name: str | None = None,
        task_type: str | None = None,
        retry_count: int = 0,
    ) -> None:
        self.task_type = task_type
        self.retry_count = retry_count
        super().__init__(message, worker_name=worker_name)


class WorkerTimeoutError(WorkerError):
    """Raised when worker task times out."""
    
    def __init__(
        self,
        message: str,
        worker_name: str | None = None,
        timeout_seconds: int = 0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message, worker_name=worker_name)


class WorkerRetryExhaustedError(WorkerError):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(
        self,
        message: str,
        worker_name: str | None = None,
        total_attempts: int = 0,
    ) -> None:
        self.total_attempts = total_attempts
        super().__init__(message, worker_name=worker_name)
