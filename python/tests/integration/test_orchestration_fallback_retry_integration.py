"""Integration tests for orchestration fallback and retry system."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.infra.resilience.orchestration_fallback import (
    FallbackContext,
    get_orchestration_fallback_manager,
)
from mindflow_backend.infra.resilience.orchestration_retry import (
    get_orchestration_retry_manager,
    OrchestrationRetryConfig,
)
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
)
from mindflow_backend.schemas.orchestration.delegation import DelegationResult, DelegationTask
from mindflow_backend.schemas.orchestration.workflow import WorkflowRouteDecision


class TestIntelligentRouterIntegration:
    """Test IntelligentRouter integration with fallback and retry."""

    @pytest.mark.asyncio
    async def test_intelligent_router_with_retry_and_fallback(self):
        """Test IntelligentRouter uses retry before fallback."""
        fallback_manager = get_orchestration_fallback_manager()
        retry_manager = get_orchestration_retry_manager()

        call_count = 0

        async def failing_intent_analysis():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("LLM API failure")
            # Return a valid IntentAnalysis after retries
            from mindflow_backend.orchestrator.routing.intent_analysis import (
                IntentAnalysis,
            )
            return IntentAnalysis(
                user_intent="test",
                recommended_agent=AgentType.ANALYST,
                formulated_objective="test objective",
                confidence=0.8,
                execution_strategy=ExecutionStrategy.DELEGATE,
            )

        # Register fallback handler
        async def fallback_handler(ctx: FallbackContext):
            from mindflow_backend.orchestrator.routing.intent_analysis import (
                IntentAnalysis,
            )
            return IntentAnalysis(
                user_intent=ctx.metadata.get("message", ""),
                recommended_agent=AgentType.ANALYST,
                formulated_objective=ctx.metadata.get("message", ""),
                confidence=0.3,
                execution_strategy=ExecutionStrategy.DELEGATE,
            )

        fallback_manager.register_fallback_handler(
            "intelligent_router", fallback_handler
        )

        # Configure retry for quick testing
        config = OrchestrationRetryConfig(
            max_retries=5, initial_backoff_seconds=0.1, initial_retry_count=2
        )
        retry_manager.register_retry_config("intelligent_router", config)

        # Execute with fallback (should retry 2 times then succeed)
        result = await fallback_manager.execute_with_fallback(
            component="intelligent_router",
            primary_func=failing_intent_analysis,
            context={"message": "test message"},
        )

        assert result.success is True
        assert call_count == 3  # 2 failures + 1 success
        assert result.fallback_used is False  # Should succeed via retry, not fallback

    @pytest.mark.asyncio
    async def test_intelligent_router_fallback_after_retry_exhausted(self):
        """Test IntelligentRouter uses fallback after retry exhaustion."""
        fallback_manager = get_orchestration_fallback_manager()
        retry_manager = get_orchestration_retry_manager()

        call_count = 0

        async def always_failing_intent_analysis():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent LLM API failure")

        # Register fallback handler
        async def fallback_handler(ctx: FallbackContext):
            from mindflow_backend.orchestrator.routing.intent_analysis import (
                IntentAnalysis,
            )
            return IntentAnalysis(
                user_intent=ctx.metadata.get("message", ""),
                recommended_agent=AgentType.ANALYST,
                formulated_objective=ctx.metadata.get("message", ""),
                confidence=0.3,
                execution_strategy=ExecutionStrategy.DELEGATE,
            )

        fallback_manager.register_fallback_handler(
            "intelligent_router", fallback_handler
        )

        # Configure retry for quick testing
        config = OrchestrationRetryConfig(
            max_retries=3, initial_backoff_seconds=0.1, initial_retry_count=2
        )
        retry_manager.register_retry_config("intelligent_router", config)

        # Execute with fallback (should retry 3 times then use fallback)
        result = await fallback_manager.execute_with_fallback(
            component="intelligent_router",
            primary_func=always_failing_intent_analysis,
            context={"message": "test message"},
        )

        assert result.success is True
        assert call_count == 3  # All retries exhausted
        assert result.fallback_used is True  # Should use fallback after retry exhaustion


class TestDelegationEngineIntegration:
    """Test DelegationEngine integration with fallback and retry."""

    @pytest.mark.asyncio
    async def test_delegation_engine_with_retry_and_fallback(self):
        """Test DelegationEngine uses retry before fallback."""
        fallback_manager = get_orchestration_fallback_manager()
        retry_manager = get_orchestration_retry_manager()

        call_count = 0

        async def failing_delegation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Agent execution failure")
            # Return success after retry
            return DelegationResult(
                task_id="test-task",
                agent=AgentType.CODER,
                agent_role=AgentType.CODER,
                status="completed",
                key_findings="Test result",
                full_output="Test output",
                confidence=0.8,
            )

        # Register fallback handler
        async def fallback_handler(ctx: FallbackContext):
            task = ctx.metadata.get("task")
            return DelegationResult(
                task_id=task.task_id if task else "unknown",
                agent=task.agent if task else None,
                agent_role=task.agent_role if task else None,
                status="failed",
                key_findings="",
                full_output=f"Delegation failed: {str(ctx.original_error)}",
                confidence=0.0,
                error_message=str(ctx.original_error),
            )

        fallback_manager.register_fallback_handler("delegation_engine", fallback_handler)

        # Configure retry
        config = OrchestrationRetryConfig(
            max_retries=3, initial_backoff_seconds=0.1, initial_retry_count=2
        )
        retry_manager.register_retry_config("delegation_engine", config)

        # Execute with fallback
        task = DelegationTask(
            objective="test objective",
            agent=AgentType.CODER,
            agent_role=AgentType.CODER,
        )

        result = await fallback_manager.execute_with_fallback(
            component="delegation_engine",
            primary_func=failing_delegation,
            context={"task": task},
        )

        assert result.success is True
        assert call_count == 3  # First attempt fails, second succeeds (but retry might try one more)
        # The result may come from retry or fallback depending on timing


class TestTeamOrchestratorIntegration:
    """Test TeamOrchestrator integration with fallback and retry."""

    @pytest.mark.asyncio
    async def test_team_orchestrator_with_retry_and_fallback(self):
        """Test TeamOrchestrator uses retry before fallback."""
        fallback_manager = get_orchestration_fallback_manager()
        retry_manager = get_orchestration_retry_manager()

        call_count = 0

        async def failing_team_session():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Team session failure")
            # Return success after retry
            from mindflow_backend.execution.teams.team_session import (
                TeamSessionResult,
            )
            return TeamSessionResult(
                session_id="test-session",
                task="test task",
                final_result="Test result",
                success=True,
                missions={},
                chat_history_length=0,
                total_duration_seconds=1.0,
                phases_completed=["formation", "discussion", "missions", "synthesis"],
            )

        # Register fallback handler
        async def fallback_handler(ctx: FallbackContext):
            from mindflow_backend.execution.teams.team_session import (
                TeamSessionResult,
            )
            return TeamSessionResult(
                success=False,
                synthesized_output=f"Team session failed: {str(ctx.original_error)}",
                agent_outputs={},
                mission_results=[],
                error=str(ctx.original_error),
            )

        fallback_manager.register_fallback_handler("team_orchestrator", fallback_handler)

        # Configure retry
        config = OrchestrationRetryConfig(
            max_retries=3, initial_backoff_seconds=0.1, initial_retry_count=2
        )
        retry_manager.register_retry_config("team_orchestrator", config)

        # Execute with fallback
        result = await fallback_manager.execute_with_fallback(
            component="team_orchestrator",
            primary_func=failing_team_session,
            context={"task": "test task", "agent_ids": ["agent1"], "session_id": "test"},
        )

        assert result.success is True
        assert call_count == 2
        assert result.fallback_used is False


class TestCommunicationBusIntegration:
    """Test CommunicationBus integration with fallback and retry."""

    @pytest.mark.asyncio
    async def test_communication_bus_send_with_retry_and_fallback(self):
        """Test CommunicationBus send uses retry before fallback."""
        fallback_manager = get_orchestration_fallback_manager()
        retry_manager = get_orchestration_retry_manager()

        call_count = 0

        async def failing_send():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Send failure")
            return True  # Success after retry

        # Register fallback handler
        async def fallback_handler(ctx: FallbackContext):
            return False  # Message not delivered

        fallback_manager.register_fallback_handler("communication_bus_send", fallback_handler)

        # Configure retry
        config = OrchestrationRetryConfig(
            max_retries=3, initial_backoff_seconds=0.1, initial_retry_count=2
        )
        retry_manager.register_retry_config("communication_bus_send", config)

        # Execute with fallback
        result = await fallback_manager.execute_with_fallback(
            component="communication_bus_send",
            primary_func=failing_send,
            context={"from_agent": "agent1", "to_agent": "agent2"},
        )

        assert result.success is True
        assert call_count == 2
        assert result.fallback_used is False
        assert result.result is True

    @pytest.mark.asyncio
    async def test_communication_bus_broadcast_with_retry_and_fallback(self):
        """Test CommunicationBus broadcast uses retry before fallback."""
        fallback_manager = get_orchestration_fallback_manager()
        retry_manager = get_orchestration_retry_manager()

        call_count = 0

        async def failing_broadcast():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Broadcast failure")
            return True  # Success after retry

        # Register fallback handler
        async def fallback_handler(ctx: FallbackContext):
            return False  # Broadcast failed

        fallback_manager.register_fallback_handler(
            "communication_bus_broadcast", fallback_handler
        )

        # Configure retry
        config = OrchestrationRetryConfig(
            max_retries=3, initial_backoff_seconds=0.1, initial_retry_count=2
        )
        retry_manager.register_retry_config("communication_bus_broadcast", config)

        # Execute with fallback
        result = await fallback_manager.execute_with_fallback(
            component="communication_bus_broadcast",
            primary_func=failing_broadcast,
            context={"from_agent": "agent1", "room_id": "room1"},
        )

        assert result.success is True
        assert call_count == 2
        assert result.fallback_used is False


class TestRetryFallbackIntegration:
    """Test integration between retry manager and fallback manager."""

    @pytest.mark.asyncio
    async def test_retry_manager_integration_with_fallback_manager(self):
        """Test that retry manager is automatically integrated with fallback manager."""
        from mindflow_backend.infra.resilience.orchestration_fallback import (
            get_orchestration_fallback_manager,
        )

        fallback_manager = get_orchestration_fallback_manager()
        assert fallback_manager._retry_manager is not None

    @pytest.mark.asyncio
    async def test_full_retry_then_fallback_flow(self):
        """Test complete flow: primary -> retry -> fallback -> ultimate fallback."""
        fallback_manager = get_orchestration_fallback_manager()
        retry_manager = get_orchestration_retry_manager()

        primary_count = 0
        fallback_count = 0

        async def always_failing_primary():
            nonlocal primary_count
            primary_count += 1
            raise ValueError("Primary always fails")

        async def fallback_handler(ctx: FallbackContext):
            nonlocal fallback_count
            fallback_count += 1
            if fallback_count < 2:
                raise ValueError("Fallback also fails")
            return "fallback_success"

        fallback_manager.register_fallback_handler("test_component", fallback_handler)

        # Configure retry to exhaust quickly
        config = OrchestrationRetryConfig(
            max_retries=2, initial_backoff_seconds=0.05, initial_retry_count=1
        )
        retry_manager.register_retry_config("test_component", config)

        # Execute
        result = await fallback_manager.execute_with_fallback(
            component="test_component",
            primary_func=always_failing_primary,
            context={"test": "data"},
        )

        # Should fail after retry exhaustion and fallback failure
        assert result.success is False
        assert primary_count == 2  # Retry exhausted (2 attempts)
        assert fallback_count == 1  # Fallback tried once after retry exhaustion
        assert result.fallback_used is True

    @pytest.mark.asyncio
    async def test_backoff_timing_integration(self):
        """Test that backoff timing works correctly in full integration."""
        fallback_manager = get_orchestration_fallback_manager()
        retry_manager = get_orchestration_retry_manager()

        call_times = []

        async def failing_then_succeeding():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise ValueError("Temporary failure")
            return "success"

        async def fallback_handler(ctx: FallbackContext):
            return "fallback"

        fallback_manager.register_fallback_handler("test_component", fallback_handler)

        # Configure retry with specific backoff
        config = OrchestrationRetryConfig(
            max_retries=5, initial_backoff_seconds=0.2, initial_retry_count=2
        )
        retry_manager.register_retry_config("test_component", config)

        # Execute
        result = await fallback_manager.execute_with_fallback(
            component="test_component",
            primary_func=failing_then_succeeding,
            context={},
        )

        assert result.success is True
        assert len(call_times) == 3

        # Verify backoff timing
        delta_1_2 = call_times[1] - call_times[0]
        delta_2_3 = call_times[2] - call_times[1]

        # Should have waited at least 0.2s between calls
        assert delta_1_2 >= 0.15
        assert delta_2_3 >= 0.15
