"""Test suite for CodingReportNode."""

import pytest


@pytest.mark.asyncio
async def test_coding_report_node_execute():
    """Test CodingReportNode execution."""
    from mindflow_backend.nodes.implementations.coding.coding_report_node import (
        CodingReportNode,
    )

    node = CodingReportNode()
    state = {
        "agent_id": "coder",
        "mission_type": "coding",
        "session_id": "test_session",
        "files_modified": ["auth.py"],
        "files_created": ["test_auth.py"],
        "verify_passed": True,
        "tests_passed": 5,
        "tests_failed": 0,
        "auto_verify_passed": True,
        "lint_report": {"errors": []},
        "type_check_report": {"errors": []},
    }

    result = await node.execute(state)

    assert isinstance(result, dict)
    assert "current_phase" in result


@pytest.mark.asyncio
async def test_coding_report_node_annotations_validation():
    """Test CodingReportNode handles non-list annotations."""
    from mindflow_backend.nodes.implementations.coding.coding_report_node import (
        CodingReportNode,
    )

    node = CodingReportNode()
    state = {
        "agent_id": "coder",
        "mission_type": "coding",
        "session_id": "test_session",
        "annotations": None,  # Invalid type
    }

    result = await node.execute(state)

    assert isinstance(result, dict)
    assert "current_phase" in result


@pytest.mark.asyncio
async def test_coding_report_node_validate_inputs():
    """Test CodingReportNode validation."""
    from mindflow_backend.nodes.implementations.coding.coding_report_node import (
        CodingReportNode,
    )

    node = CodingReportNode()
    state = {}

    errors = node.validate_inputs(state)

    assert len(errors) > 0
    assert any("agent_id" in error for error in errors)
