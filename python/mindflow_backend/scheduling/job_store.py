/"""Job persistence layer using PostgreSQL.

Adapted from Claude Code CLI's src/utils/cronTasks.ts pattern.
Stores scheduled jobs (cron and loop) in a PostgreSQL table via asyncpg.

The store provides CRUD operations and a "due jobs" query for the scheduler loop.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import asyncpg

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.scheduling.types import JobStatus

_logger = get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id VARCHAR(12) PRIMARY KEY,
    job_type VARCHAR(10) NOT NULL,
    cron VARCHAR(100),
    interval_seconds INTEGER,
    prompt TEXT NOT NULL,
    recurring BOOLEAN DEFAULT true,
    agent_id VARCHAR(50),
    max_iterations INTEGER,
    iteration_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    last_fired_at TIMESTAMP
);
"""

MAX_JOBS = 50


class JobStore:
    """PostgreSQL-backed job persistence for the scheduling module.

    Uses an asyncpg connection pool for database access.

    Usage:
        store = JobStore(pool)
        await store.initialize()
        job_id = await store.add_cron_job("*/5 * * * *", "Health check")
        jobs = await store.list_jobs()
        await store.remove_job(job_id)
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def initialize(self) -> None:
        """Create the scheduled_jobs table if it doesn't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE_SQL)
        _logger.info("job_store_initialized")

    async def add_cron_job(
        self,
        cron: str,
        prompt: str,
        recurring: bool = True,
        agent_id: str | None = None,
    ) -> str:
        """Add a new cron job and return its ID.

        Args:
            cron: 5-field cron expression.
            prompt: The prompt to execute on fire.
            recurring: If True, fire repeatedly; if False, fire once then delete.
            agent_id: Optional agent identifier.

        Returns:
            The generated job ID (12 hex chars).

        Raises:
            RuntimeError: If the maximum number of jobs is reached.
        """
        count = await self._count_jobs()
        if count >= MAX_JOBS:
            raise RuntimeError(
                f"Too many scheduled jobs (max {MAX_JOBS}). Cancel one first."
            )

        import uuid

        job_id = uuid.uuid4().hex[:12]

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scheduled_jobs
                    (id, job_type, cron, prompt, recurring, agent_id, status)
                VALUES ($1, 'cron', $2, $3, $4, $5, 'pending')
                """,
                job_id,
                cron,
                prompt,
                recurring,
                agent_id,
            )

        _logger.info("cron_job_added", id=job_id, cron=cron, recurring=recurring)
        return job_id

    async def add_loop_job(
        self,
        interval_seconds: int,
        prompt: str,
        max_iterations: int | None = None,
        agent_id: str | None = None,
    ) -> str:
        """Add a new loop job and return its ID."""
        count = await self._count_jobs()
        if count >= MAX_JOBS:
            raise RuntimeError(
                f"Too many scheduled jobs (max {MAX_JOBS}). Cancel one first."
            )

        import uuid

        job_id = uuid.uuid4().hex[:12]

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scheduled_jobs
                    (id, job_type, interval_seconds, prompt, max_iterations,
                     agent_id, status)
                VALUES ($1, 'loop', $2, $3, $4, $5, 'pending')
                """,
                job_id,
                interval_seconds,
                prompt,
                max_iterations,
                agent_id,
            )

        _logger.info(
            "loop_job_added",
            id=job_id,
            interval=interval_seconds,
            max_iterations=max_iterations,
        )
        return job_id

    async def list_jobs(
        self, agent_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List all scheduled jobs, optionally filtered by agent_id."""
        async with self._pool.acquire() as conn:
            if agent_id:
                rows = await conn.fetch(
                    "SELECT * FROM scheduled_jobs WHERE agent_id = $1 ORDER BY created_at",
                    agent_id,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM scheduled_jobs ORDER BY created_at"
                )
        return [dict(row) for row in rows]

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get a single job by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM scheduled_jobs WHERE id = $1", job_id
            )
        return dict(row) if row else None

    async def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID. Returns True if deleted."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM scheduled_jobs WHERE id = $1", job_id
            )
        deleted = result == "DELETE 1"
        if deleted:
            _logger.info("job_removed", id=job_id)
        return deleted

    async def update_job_status(self, job_id: str, status: JobStatus) -> bool:
        """Update the status of a job. Returns True if updated."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE scheduled_jobs SET status = $1 WHERE id = $2",
                status.value,
                job_id,
            )
        return result == "UPDATE 1"

    async def mark_fired(self, job_id: str) -> None:
        """Mark a job as fired (update last_fired_at timestamp)."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE scheduled_jobs SET last_fired_at = NOW() WHERE id = $1",
                job_id,
            )

    async def increment_iteration(self, job_id: str) -> int:
        """Increment the iteration count for a loop job. Returns new count."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE scheduled_jobs
                SET iteration_count = iteration_count + 1
                WHERE id = $1
                RETURNING iteration_count
                """,
                job_id,
            )
        return row["iteration_count"] if row else 0

    async def get_due_cron_jobs(self, now: datetime) -> list[dict[str, Any]]:
        """Get all active cron jobs (candidates for firing).

        The scheduler checks cron expressions against `now` after fetching.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM scheduled_jobs
                WHERE job_type = 'cron'
                  AND status IN ('pending', 'running')
                ORDER BY created_at
                """
            )
        return [dict(row) for row in rows]

    async def get_due_loop_jobs(self, now: datetime) -> list[dict[str, Any]]:
        """Get loop jobs that are due for execution.

        A loop job is due if:
        - status is 'pending' or 'running'
        - last_fired_at IS NULL (never fired)
        - last_fired_at + interval_seconds <= now
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM scheduled_jobs
                WHERE job_type = 'loop'
                  AND status IN ('pending', 'running')
                  AND (last_fired_at IS NULL
                       OR last_fired_at
                          + (interval_seconds || ' seconds')::interval <= $1)
                ORDER BY created_at
                """,
                now,
            )
        return [dict(row) for row in rows]

    async def cleanup_completed(self) -> int:
        """Remove completed, failed, or cancelled jobs. Returns count removed."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM scheduled_jobs
                WHERE status IN ('completed', 'failed', 'cancelled')
                """
            )
        count = int(result.split()[-1]) if result.startswith("DELETE") else 0
        if count > 0:
            _logger.info("jobs_cleaned_up", count=count)
        return count

    async def _count_jobs(self) -> int:
        """Count all active (non-terminal) jobs."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) as cnt FROM scheduled_jobs
                WHERE status NOT IN ('completed', 'failed', 'cancelled')
                """
            )
        return row["cnt"] if row else 0