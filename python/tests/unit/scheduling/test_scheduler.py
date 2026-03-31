"""Tests for the scheduler module.

These tests use mocks to avoid requiring a real PostgreSQL connection.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.scheduling.types import CronJob, JobStatus, JobType, LoopJob


class TestCronJob:
    """Tests for CronJob dataclass."""

    def test_default_values(self) -> None:
        job = CronJob()
        assert len(job.id) == 12
        assert job.cron == ""
        assert job.prompt == ""
        assert job.recurring is True
        assert job.agent_id is None
        assert job.status == JobStatus.PENDING
        assert job.last_fired_at is None

    def test_custom_values(self) -> None:
        job = CronJob(
            id="abc123",
            cron="*/5 * * * *",
            prompt="Health check",
            recurring=False,
            agent_id="agent-1",
        )
        assert job.id == "abc123"
        assert job.cron == "*/5 * * * *"
        assert job.prompt == "Health check"
        assert job.recurring is False
        assert job.agent_id == "agent-1"

    def test_immutable(self) -> None:
        job = CronJob(id="test")
        with pytest.raises(AttributeError):
            job.id = "changed"  # type: ignore[misc]


class TestLoopJob:
    """Tests for LoopJob dataclass."""

    def test_default_values(self) -> None:
        job = LoopJob()
        assert len(job.id) == 12
        assert job.interval_seconds == 60
        assert job.prompt == ""
        assert job.max_iterations is None
        assert job.status == JobStatus.PENDING
        assert job.iteration_count == 0

    def test_custom_values(self) -> None:
        job = LoopJob(
            interval_seconds=300,
            prompt="Sync data",
            max_iterations=10,
        )
        assert job.interval_seconds == 300
        assert job.prompt == "Sync data"
        assert job.max_iterations == 10

    def test_immutable(self) -> None:
        job = LoopJob(id="test")
        with pytest.raises(AttributeError):
            job.id = "changed"  # type: ignore[misc]


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_values(self) -> None:
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"


class TestJobType:
    """Tests for JobType enum."""

    def test_values(self) -> None:
        assert JobType.CRON.value == "cron"
        assert JobType.LOOP.value == "loop"


class TestScheduler:
    """Tests for Scheduler class."""

    @pytest.mark.asyncio
    async def test_add_and_remove_cron_job(self) -> None:
        """Test adding and removing a cron job via the store mock."""
        from mindflow_backend.scheduling.job_store import JobStore
        from mindflow_backend.scheduling.scheduler import Scheduler

        store = MagicMock(spec=JobStore)
        store.initialize = AsyncMock()
        store.add_cron_job = AsyncMock(return_value="test-job-id")
        store.remove_job = AsyncMock(return_value=True)

        fired: list[tuple[str, dict]] = []
        async def on_fire(job_id: str, job: dict) -> None:
            fired.append((job_id, job))

        scheduler = Scheduler(store, on_fire)
        await scheduler.initialize()

        job_id = await scheduler.add_cron_job("*/5 * * * *", "Test")
        assert job_id == "test-job-id"
        store.add_cron_job.assert_called_once_with(
            "*/5 * * * *", "Test", True, None
        )

        result = await scheduler.remove_job("test-job-id")
        assert result is True
        store.remove_job.assert_called_once_with("test-job-id")

    @pytest.mark.asyncio
    async def test_add_loop_job(self) -> None:
        """Test adding a loop job via the store mock."""
        from mindflow_backend.scheduling.job_store import JobStore
        from mindflow_backend.scheduling.scheduler import Scheduler

        store = MagicMock(spec=JobStore)
        store.initialize = AsyncMock()
        store.add_loop_job = AsyncMock(return_value="loop-id")

        async def on_fire(job_id: str, job: dict) -> None:
            pass

        scheduler = Scheduler(store, on_fire)
        await scheduler.initialize()

        job_id = await scheduler.add_loop_job(300, "Sync", max_iterations=5)
        assert job_id == "loop-id"
        store.add_loop_job.assert_called_once_with(
            300, "Sync", 5, None
        )

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        """Test starting and stopping the scheduler."""
        from mindflow_backend.scheduling.job_store import JobStore
        from mindflow_backend.scheduling.scheduler import Scheduler

        store = MagicMock(spec=JobStore)
        store.initialize = AsyncMock()
        store.get_due_cron_jobs = AsyncMock(return_value=[])
        store.get_due_loop_jobs = AsyncMock(return_value=[])

        async def on_fire(job_id: str, job: dict) -> None:
            pass

        scheduler = Scheduler(store, on_fire, tick_interval=0.05)
        assert scheduler.is_running is False

        await scheduler.start()
        assert scheduler.is_running is True

        # Let it tick once
        await asyncio.sleep(0.1)

        await scheduler.stop()
        assert scheduler.is_running is False

    def test_get_scheduler_requires_args(self) -> None:
        """Test that get_scheduler raises on first call without args."""
        from mindflow_backend.scheduling.scheduler import get_scheduler

        # Reset global singleton
        import mindflow_backend.scheduling.scheduler as mod
        mod._scheduler = None

        with pytest.raises(ValueError, match="store and on_fire are required"):
            get_scheduler()