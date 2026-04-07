"""Test suite for ImplementNode."""

import pytest
import tempfile
from pathlib import Path


@pytest.mark.asyncio
async def test_implement_node_execute():
    """Test ImplementNode execution."""
    from mindflow_backend.nodes.implementations.coding.implement_node import (
        ImplementNode,
    )

    node = ImplementNode()
    state = {
        "task": "Implement user authentication",
        "agent_id": "coder",
        "mission_type": "coding",
        "implementation_plan": {
            "steps": [
                {
                    "step_id": 1,
                    "description": "Analyze code",
                    "action": "analyze",
                    "files": [],
                },
                {
                    "step_id": 2,
                    "description": "Implement",
                    "action": "implement",
                    "files": [],
                },
            ]
        },
        "working_directory": "/tmp/test",
        "enabled_tools": {"FILESYSTEM": []},
    }

    result = await node.execute(state)

    assert isinstance(result, dict)
    assert "current_phase" in result


@pytest.mark.asyncio
async def test_implement_node_with_files():
    """Test ImplementNode with actual file creation."""
    from mindflow_backend.nodes.implementations.coding.implement_node import (
        ImplementNode,
    )

    node = ImplementNode()

    with tempfile.TemporaryDirectory() as tmpdir:
        state = {
            "task": "Implement user authentication",
            "agent_id": "coder",
            "mission_type": "coding",
            "implementation_plan": {
                "steps": [
                    {
                        "step_id": 1,
                        "description": "Implement",
                        "action": "implement",
                        "files": [],
                    }
                ]
            },
            "working_directory": tmpdir,
            "enabled_tools": {"FILESYSTEM": []},
        }

        result = await node.execute(state)

        assert isinstance(result, dict)
        assert "current_phase" in result


@pytest.mark.asyncio
async def test_implement_node_validate_inputs():
    """Test ImplementNode validation."""
    from mindflow_backend.nodes.implementations.coding.implement_node import (
        ImplementNode,
    )

    node = ImplementNode()
    state = {}

    errors = node.validate_inputs(state)

    assert len(errors) > 0
