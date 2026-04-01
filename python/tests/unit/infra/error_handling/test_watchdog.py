"""Tests for streaming watchdog."""

import time
import pytest

from mindflow_backend.infra.error_handling.watchdog import StreamingWatchdog


class TestStreamingWatchdog:
    """Tests for StreamingWatchdog class."""

    def test_initial_state_is_healthy(self):
        """Watchdog should be healthy on creation."""
        watchdog = StreamingWatchdog(timeout=30.0)
        assert watchdog.check() is True
        assert watchdog.is_aborted is False

    def test_reset_updates_activity(self):
        """Reset should update last activity time."""
        watchdog = StreamingWatchdog(timeout=0.1)
        time.sleep(0.05)
        watchdog.reset()
        assert watchdog.check() is True

    def test_timeout_triggers_abort(self):
        """Watchdog should abort after timeout."""
        watchdog = StreamingWatchdog(timeout=0.05)
        time.sleep(0.1)
        assert watchdog.check() is False
        assert watchdog.is_aborted is True

    def test_manual_abort(self):
        """Manual abort should mark watchdog as aborted."""
        watchdog = StreamingWatchdog(timeout=30.0)
        watchdog.abort()
        assert watchdog.is_aborted is True
        assert watchdog.check() is False

    def test_on_timeout_callback(self):
        """on_timeout callback should be called when timeout occurs."""
        callback_called = []

        def on_timeout():
            callback_called.append(True)

        watchdog = StreamingWatchdog(timeout=0.05, on_timeout=on_timeout)
        time.sleep(0.1)
        watchdog.check()
        assert len(callback_called) == 1

    def test_elapsed_since_activity(self):
        """elapsed_since_activity should return time since last reset."""
        watchdog = StreamingWatchdog(timeout=30.0)
        time.sleep(0.1)
        elapsed = watchdog.elapsed_since_activity
        assert elapsed >= 0.1
