"""Test suite for DependencyAnalysisNode."""

import pytest
import tempfile
from pathlib import Path


@pytest.mark.asyncio
async def test_dependency_analysis_node_python():
    """Test DependencyAnalysisNode for Python project."""
    from mindflow_backend.nodes.implementations.coding.dependency_analysis_node import (
        DependencyAnalysisNode,
    )

    node = DependencyAnalysisNode()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create requirements.txt with version specs
        req_file = Path(tmpdir) / "requirements.txt"
        req_file.write_text(
            "flask>=2.0.0\nrequests==2.28.0\npytest~=7.0.0\nnumpy<2.0.0\n"
        )

        state = {
            "working_directory": tmpdir,
            "project_context": {"project_type": "python"},
        }

        result = await node.execute(state)

        assert isinstance(result, dict)
        assert "current_phase" in result
        # The node returns dependencies_analysis with the parsed dependencies
        assert "dependencies_analysis" in result


@pytest.mark.asyncio
async def test_dependency_analysis_node_javascript():
    """Test DependencyAnalysisNode for JavaScript project."""
    from mindflow_backend.nodes.implementations.coding.dependency_analysis_node import (
        DependencyAnalysisNode,
    )

    node = DependencyAnalysisNode()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package.json
        import json

        package_file = Path(tmpdir) / "package.json"
        package_file.write_text(
            json.dumps(
                {
                    "dependencies": {"express": "^4.18.0", "lodash": "^4.17.21"},
                    "devDependencies": {"jest": "^29.0.0"},
                }
            )
        )

        state = {
            "working_directory": tmpdir,
            "project_context": {"project_type": "javascript"},
        }

        result = await node.execute(state)

        assert isinstance(result, dict)
        assert "current_phase" in result
        assert "dependencies_analysis" in result


@pytest.mark.asyncio
async def test_dependency_analysis_node_validate_inputs():
    """Test DependencyAnalysisNode validation."""
    from mindflow_backend.nodes.implementations.coding.dependency_analysis_node import (
        DependencyAnalysisNode,
    )

    node = DependencyAnalysisNode()
    state = {}

    errors = node.validate_inputs(state)

    assert len(errors) > 0
