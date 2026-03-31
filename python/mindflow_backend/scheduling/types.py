"""Scheduling types and data structures.

Defines the core types for the scheduling module: job types, statuses,
and immutable dataclasses for cron and loop jobs.

Pattern adapted from Claude Code CLI's CronTask type in src/utils/cronTasks.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class JobStatus(Enum):
    """Lifecycle status of a scheduled job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """Type of scheduled job."""

    CRON = "cron"  # Recurring or one-shot via cron expression
    LOOP = "loop"  # Fixed-interval loop


@dataclass(frozen=True)
class CronJob:
    """A job scheduled via cron expression.

    Attributes:
        id: Short unique identifier (12 hex chars).
        cron: Standard 5-field cron expression (e.g. "*/5 * * * *").
        prompt: The prompt to execute when the job fires.
        recurring: If True, fire on every cron match; if False, fire once then delete.
        agent_id: Optional agent responsible for this job.
        created_at: When the job was created.
        last_fired_at: When the job last fired (None if never).
        status: Current lifecycle status.
    """

    id: str = field(default_factory=lambda: uuid4().hex[:12])
    cron: str = ""
    prompt: str = ""
    recurring: bool = True
    agent_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_fired_at: datetime | None = None
    status: JobStatus = JobStatus.PENDING


@dataclass(frozen=True)
class LoopJob:
    """A job that runs at a fixed interval.

    Attributes:
        id: Short unique identifier (12 hex chars).
        interval_seconds: Seconds between executions.
        prompt: The prompt to execute each iteration.
        max_iterations: Maximum iterations (None = infinite).
        agent_id: Optional agent responsible for this job.
        created_at: When the job was created.
        iteration_count: Number of completed iterations.
        status: Current lifecycle status.
    """

    id: str = field(default_factory=lambda: uuid4().hex[:12])
    interval_seconds: int = 60
    prompt: str = ""
    max_iterations: int | None = None
    agent_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    iteration_count: int = 0
    status: JobStatus = JobStatus.PENDING


# Union type for all job types
ScheduledJob = CronJob | LoopJob