"""Loop job executor.

Handles execution of fixed-interval loop jobs. Tracks iteration counts
and respects max_iterations limits.

Pattern adapted from CacheWarmer's _warming_worker loop in
mindflow_backend/infra/cache/warming.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.scheduling.job_store import JobStore
from mindflow_backend.scheduling.types import JobStatus

_logger = get_logger(__name__)


class LoopExecutor:
    """Executes fixed-interval loop jobs.

    Checks active loop jobs from the store, determines which are due
    based on interval timing, and fires them via a callback.

    Usage:
        executor = LoopExecutor(store, on_fire=my_callback)
        await executor.tick(now=datetime.utcnow())
    """

    def __init__(
        self,
        store: JobStore,
        on_fire: Callable[[str, dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Initialize the loop executor.

        Args:
            store: Job store for persistence.
            on_fire: Async callback invoked with (job_id, job_dict) when a job fires.
        """
        self._store = store
        self._on_fire = on_fire

    async def tick(self, now: datetime) -> list[str]:
        """Check and fire due loop jobs.

        For each active loop job:
        1. Check if enough time has elapsed since last_fired_at
        2. Check if max_iterations has been reached
        3. If due, fire the job and increment iteration count

        Args:
            now: Current datetime.

        Returns:
            List of job IDs that were fired.
        """
        jobs = await self._store.get_due_loop_jobs(now)
        fired_ids: list[str] = []

        for job in jobs:
            job_id = job["id"]
            max_iterations = job.get("max_iterations")
            iteration_count = job.get("iteration_count", 0)

            # Check max iterations
            if max_iterations is not None and iteration_count >= max_iterations:
                _logger.info(
                    "loop_job_max_iterations_reached",
                    id=job_id,
                    iterations=iteration_count,
                    max=max_iterations,
                )
                await self._store.update_job_status(job_id, JobStatus.COMPLETED)
                continue

            await self._fire_job(job)
            fired_ids.append(job_id)

        return fired_ids

    async def _fire_job(self, job: dict[str, Any]) -> None:
        """Fire a single loop job.

        Args:
            job: Job dict from the store.
        """
        job_id = job["id"]
        interval = job.get("interval_seconds", 60)
        max_iterations = job.get("max_iterations")

        _logger.info(
            "loop_job_firing",
            id=job_id,
            interval=interval,
        )

        # Mark as running
        await self._store.update_job_status(job_id, JobStatus.RUNNING)

        try:
            # Invoke the callback
            await self._on_fire(job_id, job)

            # Mark as fired and increment iteration
            await self._store.mark_fired(job_id)
            new_count = await self._store.increment_iteration(job_id)

            # Check if we just hit max iterations
            if max_iterations is not None and new_count >= max_iterations:
                await self._store.update_job_status(job_id, JobStatus.COMPLETED)
                _logger.info(
                    "loop_job_completed",
                    id=job_id,
                    total_iterations=new_count,
                )
            else:
                # Reset to pending for next cycle
                await self._store.update_job_status(job_id, JobStatus.PENDING)

        except Exception as e:
            _logger.error("loop_job_fire_error", id=job_id, error=str(e))
            await self._store.update_job_status(job_id, JobStatus.FAILED)