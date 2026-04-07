"""Test suite for P2P helper utilities."""

import pytest


@pytest.mark.asyncio
async def test_check_p2p_availability():
    """Test P2P availability check."""
    from mindflow_backend.nodes.implementations.coding.utils import check_p2p_availability

    state = {}
    result = await check_p2p_availability(state)

    assert isinstance(result, dict)
    assert "available" in result


@pytest.mark.asyncio
async def test_consult_analyst_architecture_unavailable():
    """Test architectural consultation when P2P is unavailable."""
    from mindflow_backend.nodes.implementations.coding.utils import (
        consult_analyst_architecture,
    )

    agent_id = "coder"
    question = "Should I use a factory pattern here?"
    state = {"mission_type": "coding", "session_id": "test_session"}

    result = await consult_analyst_architecture(agent_id, question, state)

    assert isinstance(result, dict)
    # When P2P is unavailable, should annotate the doubt
    assert "annotated" in result or "response" in result


@pytest.mark.asyncio
async def test_notify_orchestrator_progress():
    """Test progress notification to orchestrator."""
    from mindflow_backend.nodes.implementations.coding.utils import (
        notify_orchestrator_progress,
    )

    agent_id = "coder"
    percentage = 50
    current_step = "implementation"
    state = {"mission_type": "coding", "session_id": "test_session"}

    result = await notify_orchestrator_progress(agent_id, percentage, current_step, state)

    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_annotate_architectural_doubt():
    """Test annotation of architectural doubt."""
    from mindflow_backend.nodes.implementations.coding.utils import (
        annotate_architectural_doubt,
    )

    question = "Should I use singleton here?"
    state = {
        "mission_type": "coding",
        "session_id": "test_session",
        "agent_id": "coder",
        "annotations": [],
    }

    result = await annotate_architectural_doubt(question, state)

    assert isinstance(result, dict)
    assert "success" in result
    # Should add annotation to state
    assert len(state.get("annotations", [])) > 0


@pytest.mark.asyncio
async def test_request_specialist_help():
    """Test requesting help from specialist."""
    from mindflow_backend.nodes.implementations.coding.utils import (
        request_specialist_help,
    )

    agent_id = "coder"
    specialist_type = "analyst"
    question = "Help with architecture decision"
    state = {"mission_type": "coding", "session_id": "test_session"}

    result = await request_specialist_help(
        agent_id, specialist_type, question, state
    )

    assert isinstance(result, dict)
    assert "success" in result


@pytest.mark.asyncio
async def test_graceful_p2p_fallback():
    """Test graceful fallback when P2P is unavailable."""
    from mindflow_backend.nodes.implementations.coding.utils import graceful_p2p_fallback

    state = {"annotations": []}
    operation = "consult_analyst"
    error = "P2P unavailable"
    annotation_content = "Architecture question"

    result = await graceful_p2p_fallback(operation, error, state, annotation_content)

    assert isinstance(result, dict)
    assert "annotation_result" in result
