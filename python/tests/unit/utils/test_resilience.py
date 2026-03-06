"""Tests for resilience module — retry and circuit breaker."""

from __future__ import annotations

import time

import pytest

from mindflow_backend.infra.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    RetryConfig,
    with_retry,
)

# ---------------------------------------------------------------------------
# Retry tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failures():
    call_count = 0

    @with_retry(RetryConfig(max_retries=3, backoff_base=0.01, backoff_max=0.05))
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("transient failure")
        return "success"

    result = await flaky_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_raises_after_max_attempts():
    @with_retry(RetryConfig(max_retries=2, backoff_base=0.01, backoff_max=0.02))
    async def always_fails():
        raise ConnectionError("persistent failure")

    with pytest.raises(ConnectionError, match="persistent failure"):
        await always_fails()


@pytest.mark.asyncio
async def test_retry_does_not_retry_on_value_error():
    """Non-retryable exceptions should propagate immediately."""
    call_count = 0

    @with_retry(RetryConfig(max_retries=3, backoff_base=0.01))
    async def raises_value_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError, match="not retryable"):
        await raises_value_error()
    assert call_count == 1


# ---------------------------------------------------------------------------
# Circuit Breaker tests
# ---------------------------------------------------------------------------


def test_circuit_breaker_starts_closed():
    cb = CircuitBreaker()
    assert cb.state == "CLOSED"
    cb.check()  # Should not raise


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(config=CircuitBreakerConfig(failure_threshold=3))

    for _ in range(3):
        cb.record_failure()

    assert cb.state == "OPEN"
    with pytest.raises(CircuitOpenError):
        cb.check()


def test_circuit_breaker_recovers_after_timeout():
    cb = CircuitBreaker(
        config=CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.01)
    )

    cb.record_failure()
    cb.record_failure()
    assert cb.state == "OPEN"

    # Wait for recovery timeout
    time.sleep(0.02)
    assert cb.state == "HALF_OPEN"

    # One successful call should close the circuit
    cb.check()
    cb.record_success()
    assert cb.state == "CLOSED"


def test_circuit_breaker_reopens_on_half_open_failure():
    cb = CircuitBreaker(
        config=CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.01)
    )

    cb.record_failure()
    cb.record_failure()
    time.sleep(0.02)
    assert cb.state == "HALF_OPEN"

    cb.record_failure()
    assert cb.state == "OPEN"
