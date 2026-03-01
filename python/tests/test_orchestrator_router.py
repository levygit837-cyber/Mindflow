"""Tests for the orchestrator keyword router."""

from omnimind_backend.orchestrator.router import route_message
from omnimind_backend.schemas.orchestrator import AgentType, ToolScope

# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------


def test_routes_to_coder_for_code_message() -> None:
    decision = route_message("Please implement a new login function")
    assert decision.agent == AgentType.CODER


def test_routes_to_analyst_for_data_message() -> None:
    decision = route_message("Analyze the performance metrics and show trends")
    assert decision.agent == AgentType.ANALYST


def test_routes_to_researcher_for_search_message() -> None:
    decision = route_message("Research the latest FastAPI documentation")
    assert decision.agent == AgentType.RESEARCHER


def test_routes_to_arch_tech_for_design_message() -> None:
    decision = route_message("Design a microservice architecture for the payment system")
    assert decision.agent == AgentType.ARCH_TECH


def test_routes_to_critic_for_review_message() -> None:
    decision = route_message("Review this code for quality and best practices")
    assert decision.agent == AgentType.CRITIC


def test_defaults_to_coder_for_ambiguous_message() -> None:
    decision = route_message("Hello, how are you?")
    assert decision.agent == AgentType.CODER


def test_decision_contains_tools() -> None:
    decision = route_message("Search the web for Python tutorials")
    assert decision.agent == AgentType.RESEARCHER
    assert ToolScope.WEB_SEARCH in decision.tools


def test_decision_contains_rationale() -> None:
    decision = route_message("Fix the bug in the authentication module")
    assert "coder" in decision.rationale.lower()


def test_decision_task_is_original_message() -> None:
    msg = "Implement a caching layer"
    decision = route_message(msg)
    assert decision.task == msg


def test_portuguese_keywords_route_correctly() -> None:
    decision = route_message("Pesquise sobre as últimas novidades em IA")
    assert decision.agent == AgentType.RESEARCHER


def test_mixed_keywords_highest_score_wins() -> None:
    # "code" → CODER, but "review", "evaluate", "quality", "improve" → CRITIC (more hits)
    decision = route_message("Review and evaluate the code quality and improve readability")
    assert decision.agent == AgentType.CRITIC
