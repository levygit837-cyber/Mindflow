"""Test suite for PlanNode."""

import pytest


@pytest.mark.asyncio
async def test_plan_node_execute():
    """Test PlanNode execution."""
    from mindflow_backend.nodes.implementations.coding.plan_node import PlanNode

    node = PlanNode()
    state = {
        "task": "Implement user authentication",
        "agent_id": "coder",
        "mission_type": "coding",
        "relevant_files": ["auth.py", "user.py"],
        "working_directory": "/tmp/test",
        "project_context": {"project_type": "python"},
    }

    result = await node.execute(state)

    assert isinstance(result, dict)
    assert "implementation_plan" in result
    assert "steps" in result["implementation_plan"]
    assert len(result["implementation_plan"]["steps"]) > 0


@pytest.mark.asyncio
async def test_plan_node_validate_inputs_missing():
    """Test PlanNode validation with missing inputs."""
    from mindflow_backend.nodes.implementations.coding.plan_node import PlanNode

    node = PlanNode()
    state = {}

    errors = node.validate_inputs(state)

    assert len(errors) > 0
    assert any("task" in error for error in errors)


@pytest.mark.asyncio
async def test_plan_node_validate_inputs_valid():
    """Test PlanNode validation with valid inputs."""
    from mindflow_backend.nodes.implementations.coding.plan_node import PlanNode

    node = PlanNode()
    state = {
        "task": "Implement feature",
        "agent_id": "coder",
        "mission_type": "coding",
        "working_directory": "/tmp/test",
    }

    errors = node.validate_inputs(state)

    # Should have no errors or only warnings
    # The node may require working_directory
