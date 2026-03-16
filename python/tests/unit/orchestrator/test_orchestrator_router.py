"""Tests for the intelligent orchestrator router.

The router is LLM-powered, so these tests stub the intent analysis step to be
deterministic and side-effect free.
"""

import pytest

from mindflow_backend.orchestrator.routing.router import route_message
from mindflow_backend.orchestrator.routing.intelligent_router import IntelligentRouter, IntentAnalysis
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ChainType,
    ExecutionStrategy,
)


@pytest.mark.asyncio
async def test_routes_coding_requests_to_coding_task_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeEngine:
        async def delegate_task(self, *_args, **_kwargs):  # noqa: ANN001
            raise AssertionError("delegate_task should not be called for CHAIN decisions")

    monkeypatch.setattr(
        "mindflow_backend.orchestrator.routing.intelligent_router.get_settings",
        lambda: type("S", (), {"default_provider": "test", "default_model": "test"})(),
        raising=True,
    )
    router = IntelligentRouter(_FakeEngine())

    async def _fake_analyze(_self, message: str, session_context: str = "") -> IntentAnalysis:
        return IntentAnalysis(
            user_intent="Implement feature X",
            needs_code_context=False,
            context_needed="",
            suggested_scope=[],
            recommended_agent=AgentType.CODER,
            recommended_specialist=None,
            formulated_objective="Implement feature X",
            confidence=0.9,
            is_multi_agent=False,
            agent_sequence=[],
            execution_strategy=ExecutionStrategy.CHAIN,
        )

    monkeypatch.setattr(IntelligentRouter, "analyze_intent_with_llm", _fake_analyze, raising=True)
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.routing.intelligent_router.get_intelligent_router",
        lambda: router,
        raising=True,
    )

    decision = await route_message("Please implement a new login function")
    assert decision.execution_strategy == ExecutionStrategy.CHAIN
    assert decision.chain_id == "coding_task"
    assert decision.chain_type == ChainType.CODING_TASK
    assert decision.agent == AgentType.CODER


@pytest.mark.asyncio
async def test_routes_non_coding_to_single_agent_without_llm_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeEngine:
        async def delegate_task(self, task, session):  # noqa: ANN001
            from mindflow_backend.schemas.orchestration.delegation import DelegationResult

            return DelegationResult(
                task_id=task.task_id,
                agent=task.agent,
                status="completed",
                key_findings="ok",
                full_output="ok",
                confidence=0.9,
                tokens_consumed=1,
            )

    monkeypatch.setattr(
        "mindflow_backend.orchestrator.routing.intelligent_router.get_settings",
        lambda: type("S", (), {"default_provider": "test", "default_model": "test"})(),
        raising=True,
    )
    router = IntelligentRouter(_FakeEngine())

    async def _fake_analyze(_self, message: str, session_context: str = "") -> IntentAnalysis:
        return IntentAnalysis(
            user_intent="Explain concept",
            needs_code_context=False,
            context_needed="",
            suggested_scope=[],
            recommended_agent=AgentType.ANALYST,
            recommended_specialist=None,
            formulated_objective="Explain concept succinctly",
            confidence=0.8,
            is_multi_agent=False,
            agent_sequence=[],
            execution_strategy=ExecutionStrategy.SINGLE_AGENT,
        )

    monkeypatch.setattr(IntelligentRouter, "analyze_intent_with_llm", _fake_analyze, raising=True)
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.routing.intelligent_router.get_intelligent_router",
        lambda: router,
        raising=True,
    )

    decision = await route_message("What is dependency injection?")
    assert decision.execution_strategy == ExecutionStrategy.SINGLE_AGENT
    assert decision.agent in {AgentType.ANALYST, AgentType.CODER, AgentType.RESEARCHER, AgentType.ORCHESTRATOR}


@pytest.mark.asyncio
async def test_router_can_select_file_analysis_when_folder_path_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeEngine:
        async def delegate_task(self, *_args, **_kwargs):  # noqa: ANN001
            raise AssertionError("delegate_task should not be called for routing-only test")

    monkeypatch.setattr(
        "mindflow_backend.orchestrator.routing.intelligent_router.get_settings",
        lambda: type("S", (), {"default_provider": "test", "default_model": "test"})(),
        raising=True,
    )
    router = IntelligentRouter(_FakeEngine())

    async def _fake_analyze(
        _self,
        message: str,
        session_context: str = "",
        folder_path: str | None = None,
        has_folder_path: bool = False,
    ) -> IntentAnalysis:
        assert folder_path == "/repo"
        assert has_folder_path is True
        return IntentAnalysis(
            user_intent=message,
            needs_code_context=True,
            context_needed="workspace",
            suggested_scope=[],
            recommended_agent=AgentType.ANALYST,
            recommended_specialist=None,
            formulated_objective="Mapear a codebase",
            confidence=0.92,
            is_multi_agent=False,
            agent_sequence=[],
            execution_strategy=ExecutionStrategy.CHAIN,
        )

    monkeypatch.setattr(IntelligentRouter, "analyze_intent_with_llm", _fake_analyze, raising=True)

    decision = await router.route_message_intelligently(
        "analise esta codebase",
        folder_path="/repo",
    )

    assert decision.execution_strategy == ExecutionStrategy.CHAIN
    assert decision.chain_id == "file_analysis"
    assert decision.chain_type == ChainType.FILE_ANALYSIS
    assert decision.agent == AgentType.ANALYST
