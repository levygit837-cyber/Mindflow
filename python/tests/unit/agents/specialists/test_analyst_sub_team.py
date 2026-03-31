"""
Tests for Analyst Sub-Team implementation.

Phase 4: Sub-Specialist Definitions (Analyst)
Tests context decomposition, multi-perspective analysis, and rational synthesis.
"""

import pytest
from unittest.mock import Mock

from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


# ---------------------------------------------------------------------------
# Test 1: ContextAnalyst Runtime Policy
# ---------------------------------------------------------------------------


def test_context_analyst_runtime_policy():
    """Test ContextAnalyst has correct runtime policy configuration."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        get_context_analyst_policy,
    )

    policy = get_context_analyst_policy()

    # Verify it's a sub-agent
    assert policy.is_sub_agent is True

    # Verify tier-2 model
    assert policy.model_tier == "tier-2"

    # Verify it has ANALYSIS capability
    assert MissionGraphType.ANALYSIS in policy.available_mission_graphs

    # Verify no sub-team support (recursion prevention)
    assert policy.supports_sub_team is False


# ---------------------------------------------------------------------------
# Test 2: LogicAnalyst Runtime Policy
# ---------------------------------------------------------------------------


def test_logic_analyst_runtime_policy():
    """Test LogicAnalyst has correct runtime policy configuration."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        get_logic_analyst_policy,
    )

    policy = get_logic_analyst_policy()

    assert policy.is_sub_agent is True
    assert policy.model_tier == "tier-2"
    assert MissionGraphType.DEEP_INVESTIGATION in policy.available_mission_graphs
    assert policy.supports_sub_team is False


# ---------------------------------------------------------------------------
# Test 3: SynthesisAnalyst Runtime Policy
# ---------------------------------------------------------------------------


def test_synthesis_analyst_runtime_policy():
    """Test SynthesisAnalyst has correct runtime policy configuration."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        get_synthesis_analyst_policy,
    )

    policy = get_synthesis_analyst_policy()

    assert policy.is_sub_agent is True
    assert policy.model_tier == "tier-2"
    assert MissionGraphType.ANALYSIS in policy.available_mission_graphs
    assert policy.supports_sub_team is False


# ---------------------------------------------------------------------------
# Test 4: Context Decomposition
# ---------------------------------------------------------------------------


def test_decompose_analysis_task_code_analysis():
    """Test decomposition of code analysis task."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        decompose_analysis_task,
    )

    task = "Analyze the authentication module for security vulnerabilities and performance issues"

    dimensions = decompose_analysis_task(task)

    # Should decompose into 3 dimensions
    assert len(dimensions) == 3
    assert "context" in dimensions
    assert "logic" in dimensions
    assert "synthesis" in dimensions

    # Context dimension should focus on dependencies and structure
    assert len(dimensions["context"]) > 0
    assert "authentication" in dimensions["context"].lower()

    # Logic dimension should focus on control flow and algorithms
    assert len(dimensions["logic"]) > 0

    # Synthesis dimension should focus on integration
    assert len(dimensions["synthesis"]) > 0


def test_decompose_analysis_task_architecture():
    """Test decomposition of architecture analysis task."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        decompose_analysis_task,
    )

    task = "Analyze the microservices architecture for scalability and maintainability"

    dimensions = decompose_analysis_task(task)

    assert len(dimensions) == 3
    assert all(key in dimensions for key in ["context", "logic", "synthesis"])
    assert all(len(val) > 0 for val in dimensions.values())


# ---------------------------------------------------------------------------
# Test 5: Sub-Agent ID Generation
# ---------------------------------------------------------------------------


def test_generate_analyst_ids():
    """Test generation of analyst sub-agent IDs."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        generate_analyst_ids,
    )

    parent_agent_id = "analyst_001"

    sub_agent_ids = generate_analyst_ids(parent_agent_id)

    # Should generate 3 IDs (context, logic, synthesis)
    assert len(sub_agent_ids) == 3

    # IDs should be unique
    assert len(set(sub_agent_ids)) == 3

    # IDs should contain parent reference and dimension
    assert any("context" in agent_id for agent_id in sub_agent_ids)
    assert any("logic" in agent_id for agent_id in sub_agent_ids)
    assert any("synthesis" in agent_id for agent_id in sub_agent_ids)


# ---------------------------------------------------------------------------
# Test 6: Multi-Perspective Synthesis
# ---------------------------------------------------------------------------


def test_synthesize_analysis_results_all_success():
    """Test synthesis when all analysts succeed."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        synthesize_analysis_results,
    )

    sub_agent_results = [
        {
            "agent_id": "analyst_001_context",
            "status": "completed",
            "result": "Context: Module depends on crypto library and session store...",
            "duration": 20.0,
        },
        {
            "agent_id": "analyst_001_logic",
            "status": "completed",
            "result": "Logic: Authentication flow has 3 main branches...",
            "duration": 25.0,
        },
        {
            "agent_id": "analyst_001_synthesis",
            "status": "completed",
            "result": "Synthesis: Overall architecture is sound but has 2 security concerns...",
            "duration": 18.0,
        },
    ]

    synthesis = synthesize_analysis_results(sub_agent_results)

    # Should include all perspectives
    assert "context" in synthesis.lower() or "Context" in synthesis
    assert "logic" in synthesis.lower() or "Logic" in synthesis
    assert "synthesis" in synthesis.lower() or "Synthesis" in synthesis

    # Should be structured
    assert len(synthesis) > 100


def test_synthesize_analysis_results_partial_failure():
    """Test synthesis when one analyst fails."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        synthesize_analysis_results,
    )

    sub_agent_results = [
        {
            "agent_id": "analyst_001_context",
            "status": "completed",
            "result": "Context analysis complete",
            "duration": 20.0,
        },
        {
            "agent_id": "analyst_001_logic",
            "status": "failed",
            "result": "",
            "duration": 5.0,
            "error": "Timeout",
        },
        {
            "agent_id": "analyst_001_synthesis",
            "status": "completed",
            "result": "Synthesis complete",
            "duration": 18.0,
        },
    ]

    synthesis = synthesize_analysis_results(sub_agent_results)

    # Should include successful results
    assert "context" in synthesis.lower()
    assert "synthesis" in synthesis.lower()

    # Should acknowledge failure
    assert len(synthesis) > 0


# ---------------------------------------------------------------------------
# Test 7: Analyst Sub-Team Config
# ---------------------------------------------------------------------------


def test_analyst_sub_team_config():
    """Test predefined Analyst sub-team configuration."""
    from mindflow_backend.execution.sub_teams.sub_team_config import (
        ANALYST_SUB_TEAM_CONFIG,
    )

    config = ANALYST_SUB_TEAM_CONFIG

    # Verify tier-2 model
    assert config.model_tier == "tier-2"

    # Verify agent count (exactly 3 for 3 perspectives)
    assert config.min_agents == 3
    assert config.max_agents == 3

    # Verify timeout
    assert config.timeout_seconds <= 60.0

    # Verify skip_discussion
    assert config.skip_discussion is True


# ---------------------------------------------------------------------------
# Test 8: Integration Helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_analyst_sub_team():
    """Test Analyst sub-team preparation."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        prepare_analyst_sub_team,
    )

    parent_agent_id = "analyst_001"
    task = "Analyze authentication module for security issues"

    sub_team_data = prepare_analyst_sub_team(parent_agent_id, task)

    # Verify structure
    assert "sub_agent_ids" in sub_team_data
    assert "dimensions" in sub_team_data
    assert "config" in sub_team_data

    # Verify 3 analysts (context, logic, synthesis)
    assert len(sub_team_data["sub_agent_ids"]) == 3

    # Verify dimensions dict has 3 keys
    assert len(sub_team_data["dimensions"]) == 3

    # Verify config
    assert isinstance(sub_team_data["config"], SubTeamConfig)


# ---------------------------------------------------------------------------
# Test 9: Dimension-Specific Prompts
# ---------------------------------------------------------------------------


def test_get_dimension_specific_prompt_context():
    """Test context-specific analysis prompt."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        get_dimension_specific_prompt,
    )

    base_task = "Analyze authentication module"
    dimension = "context"

    prompt = get_dimension_specific_prompt(base_task, dimension)

    # Should include dimension focus
    assert "context" in prompt.lower()
    assert "authentication" in prompt.lower()

    # Should guide analysis direction
    assert len(prompt) > len(base_task)


def test_get_dimension_specific_prompt_logic():
    """Test logic-specific analysis prompt."""
    from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
        get_dimension_specific_prompt,
    )

    base_task = "Analyze payment processing"
    dimension = "logic"

    prompt = get_dimension_specific_prompt(base_task, dimension)

    assert "logic" in prompt.lower() or "flow" in prompt.lower()
    assert "payment" in prompt.lower()
