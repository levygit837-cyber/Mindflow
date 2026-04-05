"""Unit tests for NegotiationTimer."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from mindflow_backend.infra.resilience.negotiation_timer import (
    NegotiationTimer,
    TimerAlert,
    TimerConfig,
    TimerPhase,
    run_timer_with_alerts,
)


class TestTimerConfig:
    """Tests for TimerConfig."""

    def test_get_alert_times_default(self):
        """Test getting alert times with default intervals."""
        config = TimerConfig(duration_seconds=30.0)
        alert_times = config.get_alert_times()
        assert alert_times == [24.0, 15.0, 6.0]  # 80%, 50%, 20% of 30

    def test_get_alert_times_custom(self):
        """Test getting alert times with custom intervals."""
        config = TimerConfig(
            duration_seconds=60.0, alert_intervals=[0.9, 0.5, 0.1]
        )
        alert_times = config.get_alert_times()
        assert alert_times == [54.0, 30.0, 6.0]  # 90%, 50%, 10% of 60

    def test_get_alert_times_sorted(self):
        """Test that alert times are sorted descending."""
        config = TimerConfig(
            duration_seconds=60.0, alert_intervals=[0.2, 0.8, 0.5]
        )
        alert_times = config.get_alert_times()
        assert alert_times == [48.0, 30.0, 12.0]  # Sorted descending


class TestNegotiationTimer:
    """Tests for NegotiationTimer."""

    def test_initialization(self):
        """Test timer initialization."""
        timer = NegotiationTimer(
            duration_seconds=30.0,
            alert_intervals=[0.8, 0.5, 0.2],
            grace_period_seconds=10.0,
            phase=TimerPhase.NEGOTIATION,
        )
        assert timer.config.duration_seconds == 30.0
        assert timer.config.grace_period_seconds == 10.0
        assert timer.config.phase == TimerPhase.NEGOTIATION
        assert timer.elapsed_seconds == 0.0

    def test_elapsed_seconds_before_start(self):
        """Test elapsed time before timer starts."""
        timer = NegotiationTimer(duration_seconds=30.0)
        assert timer.elapsed_seconds == 0.0

    def test_remaining_seconds_before_start(self):
        """Test remaining time before timer starts."""
        timer = NegotiationTimer(duration_seconds=30.0)
        assert timer.remaining_seconds == 30.0

    def test_percentage_elapsed_before_start(self):
        """Test percentage elapsed before timer starts."""
        timer = NegotiationTimer(duration_seconds=30.0)
        assert timer.percentage_elapsed == 0.0

    def test_is_expired_before_start(self):
        """Test is_expired before timer starts."""
        timer = NegotiationTimer(duration_seconds=30.0)
        assert timer.is_expired is False

    def test_is_in_grace_period_before_start(self):
        """Test is_in_grace_period before timer starts."""
        timer = NegotiationTimer(duration_seconds=30.0)
        assert timer.is_in_grace_period is False

    def test_is_fully_expired_before_start(self):
        """Test is_fully_expired before timer starts."""
        timer = NegotiationTimer(duration_seconds=30.0)
        assert timer.is_fully_expired is False

    def test_cancel(self):
        """Test cancelling the timer."""
        timer = NegotiationTimer(duration_seconds=30.0)
        timer.cancel()
        assert timer._cancelled is True

    def test_get_alerts_triggered_empty(self):
        """Test getting alerts when none triggered."""
        timer = NegotiationTimer(duration_seconds=30.0)
        alerts = timer.get_alerts_triggered()
        assert alerts == []

    async def test_run_short_duration(self):
        """Test running timer with short duration."""
        timer = NegotiationTimer(duration_seconds=0.5, alert_intervals=[])
        alert_callback = MagicMock()
        expiry_callback = MagicMock()

        await timer.run(
            on_alert_callback=alert_callback,
            on_expiry_callback=expiry_callback,
        )

        assert expiry_callback.called
        assert timer.elapsed_seconds >= 0.5

    async def test_run_with_alerts(self):
        """Test running timer with alerts."""
        alerts_received = []

        async def alert_callback(alert: TimerAlert):
            alerts_received.append(alert)

        timer = NegotiationTimer(
            duration_seconds=1.0, alert_intervals=[0.8, 0.5, 0.2]
        )

        await timer.run(on_alert_callback=alert_callback)

        # Should trigger all alerts
        assert len(alerts_received) == 3
        assert all(isinstance(alert, TimerAlert) for alert in alerts_received)

    async def test_run_with_sync_alert_callback(self):
        """Test running timer with synchronous alert callback."""
        alerts_received = []

        def alert_callback(alert: TimerAlert):
            alerts_received.append(alert)

        timer = NegotiationTimer(
            duration_seconds=1.0, alert_intervals=[0.5]
        )

        await timer.run(on_alert_callback=alert_callback)

        assert len(alerts_received) == 1

    async def test_run_with_expiry_callback(self):
        """Test running timer with expiry callback."""
        expiry_called = False

        async def expiry_callback():
            nonlocal expiry_called
            expiry_called = True

        timer = NegotiationTimer(duration_seconds=0.5, alert_intervals=[])

        await timer.run(on_expiry_callback=expiry_callback)

        assert expiry_called is True

    async def test_run_cancellation(self):
        """Test cancelling timer during execution."""
        timer = NegotiationTimer(duration_seconds=10.0, alert_intervals=[])

        async def cancel_after_delay():
            await asyncio.sleep(0.1)
            timer.cancel()

        await asyncio.gather(timer.run(), cancel_after_delay())

        assert timer._cancelled is True
        assert timer.elapsed_seconds < 10.0

    async def test_grace_period(self):
        """Test grace period after expiry."""
        timer = NegotiationTimer(
            duration_seconds=0.5, grace_period_seconds=0.3, alert_intervals=[]
        )

        start = datetime.now()
        await timer.run()
        elapsed = (datetime.now() - start).total_seconds()

        # Should take at least duration + grace period
        assert elapsed >= 0.8  # 0.5 + 0.3

    async def test_alert_message_format(self):
        """Test alert message format."""
        alerts_received = []

        async def alert_callback(alert: TimerAlert):
            alerts_received.append(alert)

        timer = NegotiationTimer(
            duration_seconds=10.0,
            alert_intervals=[0.8],
            phase=TimerPhase.NEGOTIATION,
        )

        await timer.run(on_alert_callback=alert_callback)

        assert len(alerts_received) == 1
        alert = alerts_received[0]
        assert "NEGOTIATION" in alert.message
        assert "time remaining" in alert.message
        assert alert.percentage_elapsed >= 0.8

    async def test_alert_metadata(self):
        """Test alert metadata."""
        alerts_received = []

        async def alert_callback(alert: TimerAlert):
            alerts_received.append(alert)

        timer = NegotiationTimer(
            duration_seconds=10.0, alert_intervals=[0.5]
        )

        await timer.run(on_alert_callback=alert_callback)

        alert = alerts_received[0]
        assert "alert_idx" in alert.metadata
        assert "remaining_seconds" in alert.metadata
        assert "percentage_remaining" in alert.metadata
        assert alert.metadata["percentage_remaining"] == 0.5

    async def test_multiple_alerts_in_order(self):
        """Test that multiple alerts trigger in order."""
        alerts_received = []

        async def alert_callback(alert: TimerAlert):
            alerts_received.append(alert)

        timer = NegotiationTimer(
            duration_seconds=1.0, alert_intervals=[0.8, 0.5, 0.2]
        )

        await timer.run(on_alert_callback=alert_callback)

        # Alerts should be in order of time (80% first, then 50%, then 20%)
        assert len(alerts_received) == 3
        assert alerts_received[0].percentage_elapsed >= 0.8
        assert alerts_received[1].percentage_elapsed >= 0.5
        assert alerts_received[2].percentage_elapsed >= 0.2

    async def test_alert_callback_exception_handling(self):
        """Test that exceptions in alert callback don't crash timer."""
        exception_count = 0

        async def failing_alert_callback(alert: TimerAlert):
            nonlocal exception_count
            exception_count += 1
            raise RuntimeError("Test error")

        timer = NegotiationTimer(
            duration_seconds=0.5, alert_intervals=[0.5]
        )

        # Should not raise exception
        await timer.run(on_alert_callback=failing_alert_callback)

        assert exception_count == 1

    async def test_expiry_callback_exception_handling(self):
        """Test that exceptions in expiry callback don't crash timer."""
        async def failing_expiry_callback():
            raise RuntimeError("Test error")

        timer = NegotiationTimer(duration_seconds=0.5, alert_intervals=[])

        # Should not raise exception
        await timer.run(on_expiry_callback=failing_expiry_callback)

        assert timer.elapsed_seconds >= 0.5


class TestRunTimerWithAlerts:
    """Tests for run_timer_with_alerts convenience function."""

    async def test_basic_usage(self):
        """Test basic usage of convenience function."""
        alerts_received = []

        async def alert_callback(alert: TimerAlert):
            alerts_received.append(alert)

        timer = await run_timer_with_alerts(
            duration_seconds=0.5,
            alert_intervals=[0.5],
            on_alert_callback=alert_callback,
        )

        assert isinstance(timer, NegotiationTimer)
        assert len(alerts_received) == 1

    async def test_with_all_parameters(self):
        """Test with all parameters."""
        alerts_received = []
        expiry_called = False

        async def alert_callback(alert: TimerAlert):
            alerts_received.append(alert)

        async def expiry_callback():
            nonlocal expiry_called
            expiry_called = True

        timer = await run_timer_with_alerts(
            duration_seconds=0.5,
            alert_intervals=[0.5],
            grace_period_seconds=0.2,
            phase=TimerPhase.CONSENSUS,
            on_alert_callback=alert_callback,
            on_expiry_callback=expiry_callback,
        )

        assert timer.config.phase == TimerPhase.CONSENSUS
        assert timer.config.grace_period_seconds == 0.2
        assert expiry_called is True


class TestTimerAlert:
    """Tests for TimerAlert dataclass."""

    def test_initialization(self):
        """Test TimerAlert initialization."""
        alert = TimerAlert(
            timestamp=datetime.now(),
            phase=TimerPhase.NEGOTIATION,
            percentage_elapsed=0.5,
            message="Test alert",
            metadata={"key": "value"},
        )

        assert alert.phase == TimerPhase.NEGOTIATION
        assert alert.percentage_elapsed == 0.5
        assert alert.message == "Test alert"
        assert alert.metadata == {"key": "value"}

    def test_default_metadata(self):
        """Test default metadata."""
        alert = TimerAlert(
            timestamp=datetime.now(),
            phase=TimerPhase.NEGOTIATION,
            percentage_elapsed=0.5,
            message="Test alert",
        )

        assert alert.metadata == {}
