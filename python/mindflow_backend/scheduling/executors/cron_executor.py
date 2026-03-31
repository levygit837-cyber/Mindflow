"""Cron job executor.

Handles firing of cron-based scheduled jobs. Checks cron expressions
against the current time and dispatches execution via a callback.

Adapted from Claude Code CLI's cronScheduler.ts fire logic.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Awaitable, Callable

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.scheduling.cron_parser import CronParseError, next_cron_run, parse_cron_expression
from mindflow_backend.scheduling.job_store import JobStore
from mindflow_backend.scheduling.types import JobStatus

_logger = get_logger(__name__)

# Jitter config: up to 10% of the period (max 15 min) for recurring,
# up to 90s for one-shot tasks (like Claude Code's DEFAULT_CRON_JITTER_CONFIG)
_MAX_RECURRING_JITTER_SECONDS = 900  # 15 minutes
_RECURRING_JITTER_RATIO = 0.10  # 10% of period
_MAX_ONESHOT_JITTER_SECONDS = 90  # 90 seconds


class CronExecutor:
    """Executes cron-based scheduled jobs.

    Checks active cron jobs from the store, determines which are due
    based on cron expression matching, and fires them via a callback.

    Usage:
        executor = CronExecutor(store, on_fire=my_callback)
        await executor.tick(now=datetime.utcnow())
    """

    def __init__(
        self,
        store: JobStore,
        on_fire: Callable[[str, dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Initialize the cron executor.

        Args:
            store: Job store for persistence.
            on_fire: Async callback invoked with (job_id, job_dict) when a job fires.
        """
        self._store = store
        self._on_fire = on_fire

    async def tick(self, now: datetime) -> list[str]:
        """Check and fire due cron jobs.

        For each active cron job:
        1. Parse the cron expression
        2. Calculate next fire time from last_fired_at (or created_at)
        3. If next_fire <= now (+ jitter), fire the job

        Args:
            now: Current datetime.

        Returns:
            List of job IDs that were fired.
        """
        jobs = await self._store.get_due_cron_jobs(now)
        fired_ids: list[str] = []

        for job in jobs:
            job_id = job["id"]
            cron = job["cron"]
            recurring = job.get("recurring", True)

            try:
                fields = parse_cron_expression(cron)
            except CronParseError as e:
                _logger.warning(
                    "cron_parse_error",
                    id=job_id,
                    cron=cron,
                    error=str(e),
                )
                await self._store.update_job_status(job_id, JobStatus.FAILED)
                continue

            # Determine the anchor time for next-fire calculation
            anchor = job.get("last_fired_at") or job["created_at"]
            if isinstance(anchor, str):
                from datetime import datetime as dt

                anchor = dt.fromisoformat(anchor)

            # Calculate next fire time
            next_fire = next_cron_run(cron, after=anchor)
            if next_fire is None:
                _logger.warning("no_next_fire", id=job_id, cron=cron)
                continue

            # Apply jitter
            jittered_fire = self._apply_jitter(next_fire, recurring)

            if jittered_fire <= now:
                await self._fire_job(job)
                fired_ids.append(job_id)

        return fired_ids

    async def _fire_job(self, job: dict[str, Any]) -> None:
        """Fire a single cron job.

        Args:
            job: Job dict from the store.
        """
        job_id = job["id"]
        recurring = job.get("recurring", True)

        _logger.info("cron_job_firing", id=job_id, cron=job["cron"])

        # Mark as running
        await self._store.update_job_status(job_id, JobStatus.RUNNING)

        try:
            # Invoke the callback
            await self._on_fire(job_id, job)

            # Mark as fired
            await self._store.mark_fired(job_id)

            if recurring:
                # Reset to pending for next cycle
                await self._store.update_job_status(job_id, JobStatus.PENDING)
            else:
                # One-shot: mark as completed (scheduler will clean up)
                await self._store.update_job_status(job_id, JobStatus.COMPLETED)
                _logger.info("one_shot_job_completed", id=job_id)

        except Exception as e:
            _logger.error("cron_job_fire_error", id=job_id, error=str(e))
            await self._store.update_job_status(job_id, JobStatus.FAILED)

    def _apply_jitter(self, fire_time: datetime, recurring: bool) -> datetime:
        """Apply deterministic jitter to a fire time.

        For recurring jobs: up to 10% of the period (max 15 min) late.
        For one-shot jobs: up to 90s early (like Claude Code's pattern).

        Args:
            fire_time: The calculated fire time.
            recurring: Whether this is a recurring job.

        Returns:
            The jittered fire time.
        """
        if recurring:
            # Recurring: push forward by up to 10% of a typical period
            # We use a fixed max to avoid needing to know the period
            jitter_seconds = random.uniform(0, _MAX_RECURRING_JITTER_SECONDS)
            from datetime import timedelta

            return fire_time + timedelta(seconds=jitter_seconds)
        else:
            # One-shot: fire up to 90s early (like Claude Code)
            jitter_seconds = random.uniform(0, _MAX_ONESHOT_JITTER_SECONDS)
            from datetime import timedelta

            return fire_time - timedelta(seconds=jitter_seconds)