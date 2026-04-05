"""Negotiation Timer - Flexible timer for orchestration phases with periodic alerts.

This module provides a timer mechanism for negotiation and consensus phases
with periodic alerts to LLMs and a grace period after expiry.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class TimerPhase(str, Enum):
    """Phases of the negotiation timer."""
    NEGOTIATION = "negotiation"
    CONSENSUS = "consensus"
    GRACE_PERIOD = "grace_period"
    EXPIRED = "expired"


@dataclass
class TimerAlert:
    """Alert event triggered during timer execution."""
    timestamp: datetime
    phase: TimerPhase
    percentage_elapsed: float
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimerConfig:
    """Configuration for the negotiation timer."""
    duration_seconds: float
    alert_intervals: list[float] = field(default_factory=lambda: [0.8, 0.5, 0.2])
    grace_period_seconds: float = 30.0
    phase: TimerPhase = TimerPhase.NEGOTIATION

    def get_alert_times(self) -> list[float]:
        """Calculate absolute times for alerts based on duration.

        Returns:
            List of absolute times in seconds when alerts should trigger
        """
        return [
            self.duration_seconds * pct
            for pct in sorted(self.alert_intervals, reverse=True)
        ]


class NegotiationTimer:
    """Flexible timer for negotiation/consensus phases with periodic alerts.

    Features:
    - Periodic alerts at configurable intervals (e.g., 80%, 50%, 20% remaining)
    - Grace period after expiry to allow LLMs to finish
    - Callback-based alert system
    - Supports cancellation and pausing

    Usage:
        timer = NegotiationTimer(
            duration_seconds=30.0,
            alert_intervals=[0.8, 0.5, 0.2],
            grace_period_seconds=30.0,
        )

        async def on_alert(alert: TimerAlert):
            print(f"Alert: {alert.message}")

        await timer.run(on_alert_callback=on_alert)
    """

    def __init__(
        self,
        duration_seconds: float,
        alert_intervals: list[float] | None = None,
        grace_period_seconds: float = 30.0,
        phase: TimerPhase = TimerPhase.NEGOTIATION,
    ):
        self.config = TimerConfig(
            duration_seconds=duration_seconds,
            alert_intervals=alert_intervals or [0.8, 0.5, 0.2],
            grace_period_seconds=grace_period_seconds,
            phase=phase,
        )
        self._start_time: datetime | None = None
        self._cancelled = False
        self._alerts_triggered: list[TimerAlert] = []
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazy-init asyncio lock for thread safety."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since timer started."""
        if self._start_time is None:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    @property
    def remaining_seconds(self) -> float:
        """Get remaining time until expiry."""
        if self._start_time is None:
            return self.config.duration_seconds
        elapsed = self.elapsed_seconds
        return max(0.0, self.config.duration_seconds - elapsed)

    @property
    def percentage_elapsed(self) -> float:
        """Get percentage of time elapsed (0.0 to 1.0)."""
        if self.config.duration_seconds == 0:
            return 1.0
        return min(1.0, self.elapsed_seconds / self.config.duration_seconds)

    @property
    def is_expired(self) -> bool:
        """Check if timer has expired."""
        return self.remaining_seconds <= 0

    @property
    def is_in_grace_period(self) -> bool:
        """Check if timer is in grace period (expired but grace not over)."""
        if not self.is_expired:
            return False
        elapsed_grace = self.elapsed_seconds - self.config.duration_seconds
        return elapsed_grace < self.config.grace_period_seconds

    @property
    def is_fully_expired(self) -> bool:
        """Check if timer is fully expired (grace period over)."""
        return self.is_expired and not self.is_in_grace_period

    def cancel(self) -> None:
        """Cancel the timer."""
        self._cancelled = True
        _logger.info(
            "negotiation_timer_cancelled",
            phase=self.config.phase.value,
            elapsed=self.elapsed_seconds,
        )

    def get_alerts_triggered(self) -> list[TimerAlert]:
        """Get list of alerts that have been triggered.

        Returns:
            List of TimerAlert objects
        """
        return self._alerts_triggered.copy()

    async def run(
        self,
        on_alert_callback: Callable[[TimerAlert], Any] | None = None,
        on_expiry_callback: Callable[[], Any] | None = None,
    ) -> None:
        """Run the timer with alert callbacks.

        Args:
            on_alert_callback: Called when an alert triggers
            on_expiry_callback: Called when timer expires (before grace period)
        """
        self._start_time = datetime.now()
        self._cancelled = False
        self._alerts_triggered.clear()

        alert_times = self.config.get_alert_times()
        next_alert_idx = 0

        _logger.info(
            "negotiation_timer_started",
            phase=self.config.phase.value,
            duration=self.config.duration_seconds,
            alert_times=alert_times,
            grace_period=self.config.grace_period_seconds,
        )

        try:
            while not self._cancelled:
                elapsed = self.elapsed_seconds

                # Check for alerts
                if next_alert_idx < len(alert_times):
                    next_alert_time = alert_times[next_alert_idx]
                    if elapsed >= next_alert_time:
                        await self._trigger_alert(
                            alert_idx=next_alert_idx,
                            alert_time=next_alert_time,
                            callback=on_alert_callback,
                        )
                        next_alert_idx += 1

                # Check for expiry
                if self.is_expired:
                    _logger.info(
                        "negotiation_timer_expired",
                        phase=self.config.phase.value,
                        elapsed=elapsed,
                    )

                    if on_expiry_callback:
                        try:
                            await on_expiry_callback()
                        except Exception as exc:
                            _logger.error(
                                "negotiation_timer_expiry_callback_failed",
                                error=str(exc),
                            )

                    # Wait for grace period
                    await asyncio.sleep(self.config.grace_period_seconds)
                    break

                # Wait a bit before next check
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            _logger.info("negotiation_timer_cancelled_asyncio")
            self._cancelled = True

        except Exception as exc:
            _logger.error(
                "negotiation_timer_error",
                phase=self.config.phase.value,
                error=str(exc),
            )
            raise

        finally:
            _logger.info(
                "negotiation_timer_finished",
                phase=self.config.phase.value,
                elapsed=self.elapsed_seconds,
                cancelled=self._cancelled,
            )

    async def _trigger_alert(
        self,
        alert_idx: int,
        alert_time: float,
        callback: Callable[[TimerAlert], Any] | None,
    ) -> None:
        """Trigger an alert at the specified time.

        Args:
            alert_idx: Index of the alert in the alert_times list
            alert_time: Absolute time when alert should trigger
            callback: Callback function to call
        """
        remaining = self.config.duration_seconds - alert_time
        percentage_remaining = remaining / self.config.duration_seconds

        alert = TimerAlert(
            timestamp=datetime.now(),
            phase=self.config.phase,
            percentage_elapsed=self.percentage_elapsed,
            message=f"{self.config.phase.value}: {percentage_remaining:.0%} time remaining ({remaining:.1f}s)",
            metadata={
                "alert_idx": alert_idx,
                "remaining_seconds": remaining,
                "percentage_remaining": percentage_remaining,
            },
        )

        self._alerts_triggered.append(alert)

        _logger.info(
            "negotiation_timer_alert_triggered",
            phase=self.config.phase.value,
            percentage_remaining=percentage_remaining,
            remaining_seconds=remaining,
        )

        if callback:
            try:
                result = callback(alert)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                _logger.error(
                    "negotiation_timer_alert_callback_failed",
                    error=str(exc),
                )


async def run_timer_with_alerts(
    duration_seconds: float,
    alert_intervals: list[float] | None = None,
    grace_period_seconds: float = 30.0,
    phase: TimerPhase = TimerPhase.NEGOTIATION,
    on_alert_callback: Callable[[TimerAlert], Any] | None = None,
    on_expiry_callback: Callable[[], Any] | None = None,
) -> NegotiationTimer:
    """Convenience function to run a timer with callbacks.

    Args:
        duration_seconds: Total duration in seconds
        alert_intervals: List of percentages for alerts (e.g., [0.8, 0.5, 0.2])
        grace_period_seconds: Grace period after expiry
        phase: Timer phase (NEGOTIATION, CONSENSUS, etc.)
        on_alert_callback: Called when alerts trigger
        on_expiry_callback: Called when timer expires

    Returns:
        NegotiationTimer instance
    """
    timer = NegotiationTimer(
        duration_seconds=duration_seconds,
        alert_intervals=alert_intervals,
        grace_period_seconds=grace_period_seconds,
        phase=phase,
    )

    await timer.run(
        on_alert_callback=on_alert_callback,
        on_expiry_callback=on_expiry_callback,
    )

    return timer
