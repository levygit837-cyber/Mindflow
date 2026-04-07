"""Test suite for ArchitectureCheckNode."""

import pytest


@pytest.mark.asyncio
async def test_architecture_check_node_python():
    """Test ArchitectureCheckNode for Python code."""
    from mindflow_backend.nodes.implementations.coding.architecture_check_node import (
        ArchitectureCheckNode,
    )

    node = ArchitectureCheckNode()
    state = {
        "files_modified": ["auth.py"],
        "working_directory": "/tmp/test",
        "agent_id": "coder",
        "mission_type": "coding",
    }

    # Mock file content with violations
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "auth.py"
        # Code with many imports (high coupling)
        code = "\n".join([f"import module{i}" for i in range(35)])
        test_file.write_text(code)

        state["working_directory"] = tmpdir
        result = await node.execute(state)

        assert isinstance(result, dict)
        # Check for expected keys
        assert "current_phase" in result


@pytest.mark.asyncio
async def test_architecture_check_node_validate_inputs():
    """Test ArchitectureCheckNode validation."""
    from mindflow_backend.nodes.implementations.coding.architecture_check_node import (
        ArchitectureCheckNode,
    )

    node = ArchitectureCheckNode()
    state = {}

    errors = node.validate_inputs(state)

    assert len(errors) > 0
