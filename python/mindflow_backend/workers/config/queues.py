"""RabbitMQ queue configuration for MindFlow workers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from mindflow_backend.infra.config import get_settings


class QueuePriority(Enum):
    """Queue priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WorkerDomain(Enum):
    """Worker domains."""
    AGENTS = "agents"
    SYSTEM = "system"
    RESEARCH = "research"


@dataclass
class QueueConfig:
    """Configuration for a RabbitMQ queue."""
    
    name: str
    domain: WorkerDomain
    worker_type: str
    priority: QueuePriority
    routing_key: str
    concurrency: int = 1
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    message_ttl: int = 3600  # seconds
    dead_letter_queue: str | None = None
    
    def get_full_queue_name(self) -> str:
        """Get the full queue name with hierarchy."""
        return f"mindflow.{self.domain.value}.{self.worker_type}.{self.priority.value}"
    
    def get_routing_key(self) -> str:
        """Get the routing key for the queue."""
        return f"{self.domain.value}.{self.worker_type}.{self.priority.value}"


class QueueDefinitions:
    """Predefined queue configurations for MindFlow."""
    
    # Agent queues
    CODER_CRITICAL = QueueConfig(
        name="coder_critical",
        domain=WorkerDomain.AGENTS,
        worker_type="coder",
        priority=QueuePriority.CRITICAL,
        routing_key="agents.coder.critical",
        concurrency=3,
        max_retries=3,
    )
    
    CODER_HIGH = QueueConfig(
        name="coder_high",
        domain=WorkerDomain.AGENTS,
        worker_type="coder",
        priority=QueuePriority.HIGH,
        routing_key="agents.coder.high",
        concurrency=2,
        max_retries=3,
    )
    
    ANALYST_HIGH = QueueConfig(
        name="analyst_high",
        domain=WorkerDomain.AGENTS,
        worker_type="analyst",
        priority=QueuePriority.HIGH,
        routing_key="agents.analyst.high",
        concurrency=2,
        max_retries=3,
    )
    
    RESEARCHER_HIGH = QueueConfig(
        name="researcher_high",
        domain=WorkerDomain.AGENTS,
        worker_type="researcher",
        priority=QueuePriority.HIGH,
        routing_key="agents.researcher.high",
        concurrency=2,
        max_retries=2,
    )
    
    ORCHESTRATOR_CRITICAL = QueueConfig(
        name="orchestrator_critical",
        domain=WorkerDomain.AGENTS,
        worker_type="orchestrator",
        priority=QueuePriority.CRITICAL,
        routing_key="agents.orchestrator.critical",
        concurrency=3,
        max_retries=3,
    )
    
    # System queues
    VECTOR_MEDIUM = QueueConfig(
        name="vector_medium",
        domain=WorkerDomain.SYSTEM,
        worker_type="vector",
        priority=QueuePriority.MEDIUM,
        routing_key="system.vector.medium",
        concurrency=1,
        max_retries=1,
        retry_delay=300,
    )
    
    MEMORY_LOW = QueueConfig(
        name="memory_low",
        domain=WorkerDomain.SYSTEM,
        worker_type="memory",
        priority=QueuePriority.LOW,
        routing_key="system.memory.low",
        concurrency=1,
        max_retries=1,
        retry_delay=600,
    )
    
    HEALTH_LOW = QueueConfig(
        name="health_low",
        domain=WorkerDomain.SYSTEM,
        worker_type="health",
        priority=QueuePriority.LOW,
        routing_key="system.health.low",
        concurrency=1,
        max_retries=0,  # Continuous monitoring
    )
    
    # Research queues
    BROWSER_HIGH = QueueConfig(
        name="browser_high",
        domain=WorkerDomain.RESEARCH,
        worker_type="browser",
        priority=QueuePriority.HIGH,
        routing_key="research.browser.high",
        concurrency=2,
        max_retries=2,
        retry_delay=180,
    )
    
    CONTENT_MEDIUM = QueueConfig(
        name="content_medium",
        domain=WorkerDomain.RESEARCH,
        worker_type="content",
        priority=QueuePriority.MEDIUM,
        routing_key="research.content.medium",
        concurrency=1,
        max_retries=2,
        retry_delay=120,
    )
    
    _ALL_QUEUES: ClassVar[list[QueueConfig]] = [
        # Agent queues
        CODER_CRITICAL, CODER_HIGH, ANALYST_HIGH, RESEARCHER_HIGH, ORCHESTRATOR_CRITICAL,
        # System queues
        VECTOR_MEDIUM, MEMORY_LOW, HEALTH_LOW,
        # Research queues
        BROWSER_HIGH, CONTENT_MEDIUM,
    ]


def get_queue_config(queue_name: str) -> QueueConfig:
    """Get queue configuration by name."""
    for queue in QueueDefinitions._ALL_QUEUES:
        if queue.name == queue_name:
            return queue
    raise ValueError(f"Queue configuration not found: {queue_name}")


def get_all_queue_configs() -> list[QueueConfig]:
    """Get all queue configurations."""
    return QueueDefinitions._ALL_QUEUES.copy()


def get_queues_by_domain(domain: WorkerDomain) -> list[QueueConfig]:
    """Get all queue configurations for a specific domain."""
    return [q for q in QueueDefinitions._ALL_QUEUES if q.domain == domain]


def get_queues_by_priority(priority: QueuePriority) -> list[QueueConfig]:
    """Get all queue configurations with a specific priority."""
    return [q for q in QueueDefinitions._ALL_QUEUES if q.priority == priority]
