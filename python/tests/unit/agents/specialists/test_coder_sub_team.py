"""
Tests for Coder Sub-Team implementation.

Phase 5: Sub-Specialist Definitions (Coder)
Tests sequential execution (Architect → Writer → Reviewer) and code quality gates.
"""

import pytest
from unittest.mock import Mock

from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


# ---------------------------------------------------------------------------
# Test 1: ArchitectAgent Runtime Policy
# ---------------------------------------------------------------------------


def test_architect_agent_runtime_policy():
    """Test ArchitectAgent has correct runtime policy configuration."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        get_architect_agent_policy,
    )

    policy = get_architect_agent_policy()

    # Verify it's a sub-agent
    assert policy.is_sub_agent is True

    # Verify tier-2 model
    assert policy.model_tier == "tier-2"

    # Verify it has ARCHITECTURE_DESIGN capability
    assert MissionGraphType.ARCHITECTURE_DESIGN in policy.available_mission_graphs

    # Verify no sub-team support
    assert policy.supports_sub_team is False


# ---------------------------------------------------------------------------
# Test 2: WriterAgent Runtime Policy
# ---------------------------------------------------------------------------


def test_writer_agent_runtime_policy():
    """Test WriterAgent has correct runtime policy configuration."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        get_writer_agent_policy,
    )

    policy = get_writer_agent_policy()

    assert policy.is_sub_agent is True
    assert policy.model_tier == "tier-2"
    assert MissionGraphType.CODING_TASK in policy.available_mission_graphs
    assert policy.supports_sub_team is False


# ---------------------------------------------------------------------------
# Test 3: ReviewerAgent Runtime Policy
# ---------------------------------------------------------------------------


def test_reviewer_agent_runtime_policy():
    """Test ReviewerAgent has correct runtime policy configuration."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        get_reviewer_agent_policy,
    )

    policy = get_reviewer_agent_policy()

    assert policy.is_sub_agent is True
    assert policy.model_tier == "tier-2"
    assert MissionGraphType.CODE_REVIEW in policy.available_mission_graphs
    assert policy.supports_sub_team is False


# ---------------------------------------------------------------------------
# Test 4: Task Decomposition for Sequential Execution
# ---------------------------------------------------------------------------


def test_decompose_coding_task():
    """Test decomposition of coding task into sequential phases."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        decompose_coding_task,
    )

    task = "Implement user authentication with JWT tokens"

    phases = decompose_coding_task(task)

    # Should decompose into 3 phases
    assert len(phases) == 3
    assert "architect" in phases
    assert "writer" in phases
    assert "reviewer" in phases

    # Architect phase should focus on design
    assert len(phases["architect"]) > 0
    assert "design" in phases["architect"].lower() or "architecture" in phases["architect"].lower()

    # Writer phase should focus on implementation
    assert len(phases["writer"]) > 0
    assert "implement" in phases["writer"].lower() or "write" in phases["writer"].lower()

    # Reviewer phase should focus on validation
    assert len(phases["reviewer"]) > 0
    assert "review" in phases["reviewer"].lower() or "validate" in phases["reviewer"].lower()


# ---------------------------------------------------------------------------
# Test 5: Sub-Agent ID Generation
# ---------------------------------------------------------------------------


def test_generate_coder_ids():
    """Test generation of coder sub-agent IDs."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        generate_coder_ids,
    )

    parent_agent_id = "coder_001"

    sub_agent_ids = generate_coder_ids(parent_agent_id)

    # Should generate 3 IDs (architect, writer, reviewer)
    assert len(sub_agent_ids) == 3

    # IDs should be unique
    assert len(set(sub_agent_ids)) == 3

    # IDs should contain parent reference and role
    assert any("architect" in agent_id for agent_id in sub_agent_ids)
    assert any("writer" in agent_id for agent_id in sub_agent_ids)
    assert any("reviewer" in agent_id for agent_id in sub_agent_ids)


# ---------------------------------------------------------------------------
# Test 6: Sequential Dependency Declaration
# ---------------------------------------------------------------------------


def test_get_execution_order():
    """Test sequential execution order is defined."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        get_execution_order,
    )

    order = get_execution_order()

    # Should define 3-step sequence
    assert len(order) == 3

    # Should be in correct order: Architect → Writer → Reviewer
    assert order[0] == "architect"
    assert order[1] == "writer"
    assert order[2] == "reviewer"


# ---------------------------------------------------------------------------
# Test 7: Code Quality Gate
# ---------------------------------------------------------------------------


def test_check_quality_gate_pass():
    """Test quality gate passes when reviewer approves."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        check_quality_gate,
    )

    reviewer_result = {
        "agent_id": "coder_001_reviewer",
        "status": "completed",
        "result": "Code review passed. No critical issues found.",
        "metadata": {"quality_score": 85, "issues": []},
    }

    passed, message = check_quality_gate(reviewer_result)

    assert passed is True
    assert len(message) > 0


def test_check_quality_gate_fail():
    """Test quality gate fails when reviewer finds critical issues."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        check_quality_gate,
    )

    reviewer_result = {
        "agent_id": "coder_001_reviewer",
        "status": "completed",
        "result": "Code review failed. Found 3 critical security issues.",
        "metadata": {
            "quality_score": 45,
            "issues": ["SQL injection", "XSS vulnerability", "Hardcoded secrets"],
        },
    }

    passed, message = check_quality_gate(reviewer_result)

    assert passed is False
    assert "critical" in message.lower() or "failed" in message.lower()


# ---------------------------------------------------------------------------
# Test 8: Result Synthesis with Sequential Context
# ---------------------------------------------------------------------------


def test_synthesize_coding_results_all_success():
    """Test synthesis when all phases succeed."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        synthesize_coding_results,
    )

    sub_agent_results = [
        {
            "agent_id": "coder_001_architect",
            "status": "completed",
            "result": "Architecture: 3 classes, 5 interfaces designed...",
            "duration": 25.0,
        },
        {
            "agent_id": "coder_001_writer",
            "status": "completed",
            "result": "Implementation: All classes and tests written...",
            "duration": 35.0,
        },
        {
            "agent_id": "coder_001_reviewer",
            "status": "completed",
            "result": "Review: Code quality approved, no critical issues...",
            "duration": 20.0,
        },
    ]

    synthesis = synthesize_coding_results(sub_agent_results)

    # Should include all phases
    assert "architect" in synthesis.lower() or "design" in synthesis.lower()
    assert "writer" in synthesis.lower() or "implementation" in synthesis.lower()
    assert "review" in synthesis.lower()

    # Should indicate success
    assert len(synthesis) > 100


def test_synthesize_coding_results_reviewer_blocks():
    """Test synthesis when reviewer blocks the code."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        synthesize_coding_results,
    )

    sub_agent_results = [
        {
            "agent_id": "coder_001_architect",
            "status": "completed",
            "result": "Architecture designed",
            "duration": 25.0,
        },
        {
            "agent_id": "coder_001_writer",
            "status": "completed",
            "result": "Implementation complete",
            "duration": 35.0,
        },
        {
            "agent_id": "coder_001_reviewer",
            "status": "completed",
            "result": "BLOCKED: Critical security issues found",
            "duration": 20.0,
            "metadata": {"quality_gate_passed": False},
        },
    ]

    synthesis = synthesize_coding_results(sub_agent_results)

    # Should indicate blocking
    assert "block" in synthesis.lower() or "failed" in synthesis.lower()


# ---------------------------------------------------------------------------
# Test 9: Coder Sub-Team Config
# ---------------------------------------------------------------------------


def test_coder_sub_team_config():
    """Test predefined Coder sub-team configuration."""
    from mindflow_backend.execution.sub_teams.sub_team_config import (
        CODER_SUB_TEAM_CONFIG,
    )

    config = CODER_SUB_TEAM_CONFIG

    # Verify tier-2 model
    assert config.model_tier == "tier-2"

    # Verify agent count (exactly 3 for sequential pipeline)
    assert config.min_agents == 3
    assert config.max_agents == 3

    # Verify timeout
    assert config.timeout_seconds <= 60.0

    # Verify skip_discussion
    assert config.skip_discussion is True


# ---------------------------------------------------------------------------
# Test 10: Integration Helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_coder_sub_team():
    """Test Coder sub-team preparation."""
    from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
        prepare_coder_sub_team,
    )

    parent_agent_id = "coder_001"
    task = "Implement JWT authentication"

    sub_team_data = prepare_coder_sub_team(parent_agent_id, task)

    # Verify structure
    assert "sub_agent_ids" in sub_team_data
    assert "phases" in sub_team_data
    assert "execution_order" in sub_team_data
    assert "config" in sub_team_data

    # Verify 3 agents (architect, writer, reviewer)
    assert len(sub_team_data["sub_agent_ids"]) == 3

    # Verify phases dict has 3 keys
    assert len(sub_team_data["phases"]) == 3

    # Verify execution order
    assert sub_team_data["execution_order"] == ["architect", "writer", "reviewer"]

    # Verify config
    assert isinstance(sub_team_data["config"], SubTeamConfig)
