"""
Tests for Researcher Sub-Team implementation.

Phase 3: Sub-Specialist Definitions (Researcher)
Tests query splitting, parallel search, and result synthesis.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from mindflow_backend.agents.specialists.runtime_policy import AgentRuntimePolicy
from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


# ---------------------------------------------------------------------------
# Test 1: TopicResearcher Runtime Policy
# ---------------------------------------------------------------------------


def test_topic_researcher_runtime_policy():
    """Test TopicResearcher has correct runtime policy configuration."""
    from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
        get_topic_researcher_policy,
    )

    policy = get_topic_researcher_policy()

    # Verify it's a sub-agent (cannot spawn sub-sub-teams)
    assert policy.is_sub_agent is True

    # Verify tier-2 model for cost control
    assert policy.model_tier == "tier-2"

    # Verify it has WEB_RESEARCH capability
    assert MissionGraphType.WEB_RESEARCH in policy.available_mission_graphs

    # Verify it does NOT support sub-teams (recursion prevention)
    assert policy.supports_sub_team is False
    assert policy.sub_team_config is None


# ---------------------------------------------------------------------------
# Test 2: Query Splitting Logic
# ---------------------------------------------------------------------------


def test_split_research_task_simple():
    """Test splitting a simple research task into sub-queries."""
    from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
        split_research_task,
    )

    task = "Research authentication methods: OAuth, JWT, and session-based auth"

    sub_queries = split_research_task(task, max_topics=3)

    # Should split into 3 topics
    assert len(sub_queries) == 3

    # Each query should be a string
    assert all(isinstance(q, str) for q in sub_queries)

    # Queries should contain relevant keywords
    query_text = " ".join(sub_queries).lower()
    assert "oauth" in query_text
    assert "jwt" in query_text
    assert "session" in query_text or "auth" in query_text


def test_split_research_task_complex():
    """Test splitting a complex multi-topic research task."""
    from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
        split_research_task,
    )

    task = """
    Research the following topics for our new microservices architecture:
    1. Service mesh patterns (Istio, Linkerd)
    2. API gateway solutions (Kong, Ambassador)
    3. Observability tools (Prometheus, Grafana, Jaeger)
    """

    sub_queries = split_research_task(task, max_topics=3)

    assert len(sub_queries) == 3

    # Verify each query is focused on one topic
    assert any("service mesh" in q.lower() or "istio" in q.lower() for q in sub_queries)
    assert any("api gateway" in q.lower() or "kong" in q.lower() for q in sub_queries)
    assert any("observability" in q.lower() or "prometheus" in q.lower() for q in sub_queries)


def test_split_research_task_single_topic():
    """Test handling of single-topic research (no splitting needed)."""
    from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
        split_research_task,
    )

    task = "Research the latest features in Python 3.12"

    sub_queries = split_research_task(task, max_topics=3)

    # Should return at least 1 query (the original task)
    assert len(sub_queries) >= 1
    assert len(sub_queries) <= 3


# ---------------------------------------------------------------------------
# Test 3: Sub-Agent ID Generation
# ---------------------------------------------------------------------------


def test_generate_topic_researcher_ids():
    """Test generation of unique sub-agent IDs."""
    from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
        generate_topic_researcher_ids,
    )

    parent_agent_id = "researcher_001"
    num_topics = 3

    sub_agent_ids = generate_topic_researcher_ids(parent_agent_id, num_topics)

    # Should generate correct number of IDs
    assert len(sub_agent_ids) == 3

    # IDs should be unique
    assert len(set(sub_agent_ids)) == 3

    # IDs should contain parent reference
    assert all(parent_agent_id in agent_id for agent_id in sub_agent_ids)

    # IDs should have topic index
    assert any("topic_0" in agent_id or "topic_1" in agent_id for agent_id in sub_agent_ids)


# ---------------------------------------------------------------------------
# Test 4: Result Synthesis
# ---------------------------------------------------------------------------


def test_synthesize_research_results_success():
    """Test synthesis of successful research results."""
    from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
        synthesize_research_results,
    )

    sub_agent_results = [
        {
            "agent_id": "researcher_001_topic_0",
            "status": "completed",
            "result": "OAuth 2.0 is an authorization framework...",
            "duration": 15.0,
        },
        {
            "agent_id": "researcher_001_topic_1",
            "status": "completed",
            "result": "JWT (JSON Web Tokens) are compact, URL-safe tokens...",
            "duration": 18.0,
        },
        {
            "agent_id": "researcher_001_topic_2",
            "status": "completed",
            "result": "Session-based authentication stores user state on the server...",
            "duration": 12.0,
        },
    ]

    synthesis = synthesize_research_results(sub_agent_results)

    # Should combine all results
    assert "OAuth" in synthesis or "oauth" in synthesis.lower()
    assert "JWT" in synthesis or "jwt" in synthesis.lower()
    assert "session" in synthesis.lower()

    # Should be structured (not just concatenation)
    assert len(synthesis) > 100  # Should have meaningful content


def test_synthesize_research_results_partial_failure():
    """Test synthesis when some sub-agents fail."""
    from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
        synthesize_research_results,
    )

    sub_agent_results = [
        {
            "agent_id": "researcher_001_topic_0",
            "status": "completed",
            "result": "OAuth 2.0 findings...",
            "duration": 15.0,
        },
        {
            "agent_id": "researcher_001_topic_1",
            "status": "failed",
            "result": "",
            "duration": 5.0,
            "error": "Timeout",
        },
        {
            "agent_id": "researcher_001_topic_2",
            "status": "completed",
            "result": "Session auth findings...",
            "duration": 12.0,
        },
    ]

    synthesis = synthesize_research_results(sub_agent_results)

    # Should include successful results
    assert "OAuth" in synthesis or "oauth" in synthesis.lower()
    assert "session" in synthesis.lower()

    # Should acknowledge failures
    assert len(synthesis) > 0  # Should still produce output


# ---------------------------------------------------------------------------
# Test 5: Researcher Sub-Team Config
# ---------------------------------------------------------------------------


def test_researcher_sub_team_config():
    """Test predefined Researcher sub-team configuration."""
    from mindflow_backend.execution.sub_teams.sub_team_config import (
        RESEARCHER_SUB_TEAM_CONFIG,
    )

    config = RESEARCHER_SUB_TEAM_CONFIG

    # Verify tier-2 model
    assert config.model_tier == "tier-2"

    # Verify agent count (2-3 for parallel research)
    assert config.min_agents == 2
    assert config.max_agents == 3

    # Verify timeout (≤60s)
    assert config.timeout_seconds <= 60.0

    # Verify skip_discussion
    assert config.skip_discussion is True


# ---------------------------------------------------------------------------
# Test 6: Integration with SubTeamLauncher
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_researcher_sub_team_integration():
    """Test Researcher sub-team integration with SubTeamLauncher."""
    from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
        prepare_researcher_sub_team,
    )

    parent_agent_id = "researcher_001"
    task = "Research OAuth, JWT, and session authentication"

    # Prepare sub-team (split task, generate IDs, get config)
    sub_team_data = prepare_researcher_sub_team(parent_agent_id, task)

    # Verify structure
    assert "sub_agent_ids" in sub_team_data
    assert "sub_queries" in sub_team_data
    assert "config" in sub_team_data

    # Verify sub-agent count matches queries
    assert len(sub_team_data["sub_agent_ids"]) == len(sub_team_data["sub_queries"])

    # Verify config is SubTeamConfig
    assert isinstance(sub_team_data["config"], SubTeamConfig)
