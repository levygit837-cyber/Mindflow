"""Main scheduler orchestrator for the scheduling module.

Adapted from:
- Claude Code CLI's cronScheduler.ts (polling loop, fire logic)
- MindFlow's CacheWarmer (asyncio task loop, worker pattern)

The Scheduler manages the lifecycle of cron and loop jobs: starting/stopping
the tick loop, adding/removing jobs, and dispatching to executors.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Awaitable, Callable

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.scheduling.executors import CronExecutor, LoopExecutor
from mindflow_backend.scheduling.job_store import JobStore

_logger = get_logger(__name__)

# Global singleton
_scheduler: Scheduler | None = None


class Scheduler:
    """Main scheduler orchestrator.

    Runs an async tick loop that checks for due cron and loop jobs,
    dispatching execution to the appropriate executor.

    Usage:
        scheduler = Scheduler(store, on_fire=my_callback)
        await scheduler.start()
        job_id = await scheduler.add_cron_job("*/5 * * * *", "Health check")
        ...
        await scheduler.stop()
    """

    def __init__(
        self,
        store: JobStore,
        on_fire: Callable[[str, dict[str, Any]], Awaitable[None]],
        tick_interval: float = 1.0,
    ) -> None:
        """Initialize the scheduler.

        Args:
            store: Job store for persistence.
            on_fire: Async callback invoked with (job_id, job_dict) when a job fires.
            tick_interval: Seconds between tick cycles (default: 1s, like Claude Code).
        """
        self._store = store
        self._on_fire = on_fire
        self._tick_interval = tick_interval

        self._cron_executor = CronExecutor(store, on_fire)
        self._loop_executor = LoopExecutor(store, on_fire)

        self._task: asyncio.Task | None = None
        self._is_running = False
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize the scheduler (create DB table, etc.)."""
        if self._is_initialized:
            return
        await self._store.initialize()
        self._is_initialized = True
        _logger.info("scheduler_initialized")

    async def start(self) -> None:
        """Start the scheduler tick loop.

        Creates the DB table if not yet initialized, then starts
        an asyncio task that ticks every `tick_interval` seconds.
        """
        if self._is_running:
            _logger.warning("scheduler_already_running")
            return

        await self.initialize()

        self._is_running = True
        self._task = asyncio.create_task(self._tick_loop())
        _logger.info("scheduler_started", tick_interval=self._tick_interval)

    async def stop(self) -> None:
        """Stop the scheduler tick loop.

        Cancels the running task and waits for it to finish.
        """
        if not self._is_running:
            return

        self._is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        _logger.info("scheduler_stopped")

    async def add_cron_job(
        self,
        cron: str,
        prompt: str,
        recurring: bool = True,
        agent_id: str | None = None,
    ) -> str:
        """Add a new cron job.

        Args:
            cron: 5-field cron expression.
            prompt: The prompt to execute on fire.
            recurring: If True, fire repeatedly; if False, fire once then delete.
            agent_id: Optional agent identifier.

        Returns:
            The generated job ID.
        """
        await self.initialize()
        return await self._store.add_cron_job(cron, prompt, recurring, agent_id)

    async def add_loop_job(
        self,
        interval_seconds: int,
        prompt: str,
        max_iterations: int | None = None,
        agent_id: str | None = None,
    ) -> str:
        """Add a new loop job.

        Args:
            interval_seconds: Seconds between executions.
            prompt: The prompt to execute each iteration.
            max_iterations: Maximum iterations (None = infinite).
            agent_id: Optional agent identifier.

        Returns:
            The generated job ID.
        """
        await self.initialize()
        return await self._store.add_loop_job(
            interval_seconds, prompt, max_iterations, agent_id
        )

    async def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID.

        Args:
            job_id: The job ID to remove.

        Returns:
            True if the job was deleted.
        """
        return await self._store.remove_job(job_id)

    async def list_jobs(
        self, agent_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List all scheduled jobs.

        Args:
            agent_id: If provided, only return jobs for this agent.

        Returns:
            List of job dicts.
        """
        return await self._store.list_jobs(agent_id)

    async def cleanup(self) -> int:
        """Remove completed, failed, and cancelled jobs.

        Returns:
            Number of jobs removed.
        """
        return await self._store.cleanup_completed()

    @property
    def is_running(self) -> bool:
        """Whether the scheduler is currently running."""
        return self._is_running

    async def _tick_loop(self) -> None:
        """Main scheduler loop.

        Runs indefinitely, ticking every `tick_interval` seconds.
        Each tick checks for due cron and loop jobs.
        """
        _logger.debug("tick_loop_started")

        while self._is_running:
            try:
                now = datetime.utcnow()

                # Fire due cron jobs
                cron_fired = await self._cron_executor.tick(now)
                if cron_fired:
                    _logger.info("cron_jobs_fired", count=len(cron_fired), ids=cron_fired)

                # Fire due loop jobs
                loop_fired = await self._loop_executor.tick(now)
                if loop_fired:
                    _logger.info("loop_jobs_fired", count=len(loop_fired), ids=loop_fired)

                await asyncio.sleep(self._tick_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("tick_loop_error", error=str(e))
                await asyncio.sleep(self._tick_interval)

        _logger.debug("tick_loop_stopped")


def get_scheduler(
    store: JobStore | None = None,
    on_fire: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
) -> Scheduler:
    """Get the global scheduler singleton.

    Args:
        store: Job store (required on first call).
        on_fire: Fire callback (required on first call).

    Returns:
        The global Scheduler instance.
    """
    global _scheduler
    if _scheduler is None:
        if store is None or on_fire is None:
            raise ValueError(
                "store and on_fire are required for first call to get_scheduler"
            )
        _scheduler = Scheduler(store, on_fire)
    return _scheduler