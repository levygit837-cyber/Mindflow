"""MindFlow Scheduling Module — Loops & Cron Jobs.

Adapted from Claude Code CLI's ScheduleCronTool pattern,
integrated with MindFlow's async architecture (asyncpg, structlog).

Provides:
- CronJob / LoopJob types for scheduled task definitions
- CronParser for 5-field cron expression parsing
- JobStore for PostgreSQL persistence
- Scheduler as the main orchestrator (asyncio-based loop)
- CronExecutor and LoopExecutor for job execution

Usage:
    from mindflow_backend.scheduling import get_scheduler

    scheduler = get_scheduler()
    await scheduler.start()
    job_id = await scheduler.add_cron_job("*/5 * * * *", "Check system health")
    await scheduler.remove_job(job_id)
    await scheduler.stop()
"""

from __future__ import annotations

from mindflow_backend.scheduling.types import (
    CronJob,
    JobStatus,
    JobType,
    LoopJob,
)
from mindflow_backend.scheduling.cron_parser import (
    CronFields,
    CronParseError,
    cron_to_human,
    next_cron_run,
    parse_cron_expression,
)
from mindflow_backend.scheduling.job_store import JobStore
from mindflow_backend.scheduling.scheduler import Scheduler, get_scheduler

__all__ = [
    # Types
    "CronJob",
    "LoopJob",
    "JobStatus",
    "JobType",
    # Cron Parser
    "CronFields",
    "CronParseError",
    "parse_cron_expression",
    "next_cron_run",
    "cron_to_human",
    # Job Store
    "JobStore",
    # Scheduler
    "Scheduler",
    "get_scheduler",
]