"""Unit tests for orchestration retry manager."""

import asyncio
from datetime import datetime

import pytest

from mindflow_backend.infra.resilience.orchestration_retry import (
    OrchestrationRetryConfig,
    OrchestrationRetryManager,
    RetryContext,
    RetryResult,
)


class TestOrchestrationRetryConfig:
    """Test OrchestrationRetryConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestrationRetryConfig()
        assert config.max_retries == 10
        assert config.initial_backoff_seconds == 5.0
        assert config.initial_retry_count == 5
        assert config.backoff_step_seconds == 10.0

    def test_backoff_for_initial_retries(self):
        """Test backoff for initial retries (first 5)."""
        config = OrchestrationRetryConfig(
            max_retries=10,
            initial_backoff_seconds=5.0,
            initial_retry_count=5,
            backoff_step_seconds=10.0,
        )

        # First 5 retries should have initial backoff
        for attempt in range(1, 6):
            backoff = config.get_backoff_for_attempt(attempt)
            assert backoff == 5.0, f"Attempt {attempt} should have 5s backoff"

    def test_backoff_for_later_retries(self):
        """Test backoff for later retries (after 5)."""
        config = OrchestrationRetryConfig(
            max_retries=10,
            initial_backoff_seconds=5.0,
            initial_retry_count=5,
            backoff_step_seconds=10.0,
        )

        # Retry 6: 5s + 1 * 10s = 15s
        assert config.get_backoff_for_attempt(6) == 15.0
        # Retry 7: 5s + 2 * 10s = 25s
        assert config.get_backoff_for_attempt(7) == 25.0
        # Retry 8: 5s + 3 * 10s = 35s
        assert config.get_backoff_for_attempt(8) == 35.0
        # Retry 9: 5s + 4 * 10s = 45s
        assert config.get_backoff_for_attempt(9) == 45.0
        # Retry 10: 5s + 5 * 10s = 55s
        assert config.get_backoff_for_attempt(10) == 55.0


class TestOrchestrationRetryManager:
    """Test OrchestrationRetryManager."""

    @pytest.fixture
    def retry_manager(self):
        """Create a retry manager for testing."""
        return OrchestrationRetryManager()

    def test_register_retry_config(self, retry_manager):
        """Test registering retry configuration."""
        config = OrchestrationRetryConfig(max_retries=5)
        retry_manager.register_retry_config("test_component", config)

        retrieved = retry_manager.get_retry_config("test_component")
        assert retrieved.max_retries == 5

    def test_get_default_config(self, retry_manager):
        """Test getting default configuration for unregistered component."""
        config = retry_manager.get_retry_config("unregistered_component")
        assert isinstance(config, OrchestrationRetryConfig)
        assert config.max_retries == 10

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, retry_manager):
        """Test successful execution with retry."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        config = OrchestrationRetryConfig(max_retries=3)
        retry_manager.register_retry_config("test", config)

        result = await retry_manager.execute_with_retry(
            "test", test_func, context={"test": "data"}
        )

        assert result.success is True
        assert result.result == "success"
        assert result.attempts_made == 1
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_failure_then_success(self, retry_manager):
        """Test retry on failure then success."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        config = OrchestrationRetryConfig(max_retries=5, initial_backoff_seconds=0.1)
        retry_manager.register_retry_config("test", config)

        result = await retry_manager.execute_with_retry("test", test_func)

        assert result.success is True
        assert result.result == "success"
        assert result.attempts_made == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_all_retries_exhausted(self, retry_manager):
        """Test all retries exhausted."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")

        config = OrchestrationRetryConfig(max_retries=3, initial_backoff_seconds=0.1)
        retry_manager.register_retry_config("test", config)

        result = await retry_manager.execute_with_retry("test", test_func)

        assert result.success is False
        assert result.error is not None
        assert result.attempts_made == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_backoff_timing(self, retry_manager):
        """Test backoff timing between retries."""
        call_times = []

        async def test_func():
            call_times.append(datetime.now())
            if len(call_times) < 3:
                raise ValueError("Temporary failure")
            return "success"

        config = OrchestrationRetryConfig(
            max_retries=5, initial_backoff_seconds=0.2, initial_retry_count=2
        )
        retry_manager.register_retry_config("test", config)

        result = await retry_manager.execute_with_retry("test", test_func)

        assert result.success is True
        assert len(call_times) == 3

        # Check that backoff was applied (time between calls)
        delta_1_2 = (call_times[1] - call_times[0]).total_seconds()
        delta_2_3 = (call_times[2] - call_times[1]).total_seconds()

        # First two retries should have initial backoff (0.2s)
        assert delta_1_2 >= 0.15  # Allow some tolerance
        # Third retry should have stepped backoff (0.2s + 1 * 0s = 0.2s)
        assert delta_2_3 >= 0.15


class TestRetryContext:
    """Test RetryContext."""

    def test_retry_context_creation(self):
        """Test creating a retry context."""
        context = RetryContext(
            component="test_component",
            attempt=3,
            max_retries=10,
            original_error="test error",
            metadata={"key": "value"},
        )

        assert context.component == "test_component"
        assert context.attempt == 3
        assert context.max_retries == 10
        assert context.original_error == "test error"
        assert context.metadata == {"key": "value"}


class TestRetryResult:
    """Test RetryResult."""

    def test_retry_result_success(self):
        """Test successful retry result."""
        result = RetryResult(
            success=True,
            result="test_result",
            attempts_made=2,
            total_duration_seconds=1.5,
        )

        assert result.success is True
        assert result.result == "test_result"
        assert result.attempts_made == 2
        assert result.total_duration_seconds == 1.5
        assert result.error is None

    def test_retry_result_failure(self):
        """Test failed retry result."""
        result = RetryResult(
            success=False,
            error="test_error",
            attempts_made=10,
            total_duration_seconds=5.0,
        )

        assert result.success is False
        assert result.error == "test_error"
        assert result.attempts_made == 10
        assert result.total_duration_seconds == 5.0
        assert result.result is None
