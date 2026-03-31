"""Tests for MissionResult and MemoryAnnotationRef."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from mindflow_backend.execution.missions.mission_result import (
    MemoryAnnotationRef,
    MissionResult,
)
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


class TestFromGraphStateSuccess:
    """Test from_graph_state with a success state."""

    def test_from_graph_state_success(self):
        """Should create a MissionResult with success=True."""
        state = {
            "mission_id": "m-abc",
            "result": "Analysis complete: found 3 issues.",
            "annotations": [
                {"content": "Issue 1", "importance": 0.8, "iteration": 2, "tags": ["bug"]},
            ],
            "messages_sent": [{"to": "leader", "type": "status"}],
            "iteration": 15,
            "errors": [],
            "metadata": {"depth": 3},
            "started_at": datetime(2026, 1, 1, 10, 0, 0),
        }

        result = MissionResult.from_graph_state(
            state=state,
            agent_id="analyst",
            mission_type=MissionGraphType.ANALYSIS,
        )

        assert result.agent_id == "analyst"
        assert result.mission_type == MissionGraphType.ANALYSIS
        assert result.mission_id == "m-abc"
        assert result.success is True
        assert result.result == "Analysis complete: found 3 issues."
        assert len(result.annotations) == 1
        assert result.annotations[0].content == "Issue 1"
        assert result.annotations[0].importance == 0.8
        assert result.annotations[0].iteration == 2
        assert result.annotations[0].tags == ["bug"]
        assert result.messages_sent == [{"to": "leader", "type": "status"}]
        assert result.iterations == 15
        assert result.error is None
        assert result.metadata == {"depth": 3}


class TestFromGraphStateError:
    """Test from_graph_state with an error state."""

    def test_from_graph_state_error(self):
        """Should create a MissionResult with success=False."""
        state = {
            "mission_id": "m-err",
            "result": "",
            "annotations": [],
            "messages_sent": [],
            "iteration": 3,
            "errors": ["Graph execution failed: timeout"],
            "metadata": {},
            "started_at": datetime(2026, 1, 1, 10, 0, 0),
        }

        result = MissionResult.from_graph_state(
            state=state,
            agent_id="coder",
            mission_type=MissionGraphType.CODING_TASK,
        )

        assert result.success is False
        assert result.error == "Graph execution failed: timeout"
        assert result.iterations == 3


class TestToDelegationResultData:
    """Test conversion to DelegationResult-compatible dict."""

    def test_to_delegation_result_data(self):
        """Dict should have all expected keys."""
        result = MissionResult(
            agent_id="analyst",
            mission_type=MissionGraphType.DEEP_INVESTIGATION,
            mission_id="m-123",
            success=True,
            result="Found the issue.",
            annotations=[
                MemoryAnnotationRef(
                    content="Key finding",
                    importance=0.9,
                    iteration=5,
                    tags=["critical"],
                ),
            ],
            messages_sent=[{"to": "orch", "body": "done"}],
            duration_seconds=45.0,
            iterations=20,
            error=None,
            started_at=datetime(2026, 1, 1, 10, 0, 0),
            completed_at=datetime(2026, 1, 1, 10, 0, 45),
        )

        data = result.to_delegation_result_data()

        assert data["status"] == "completed"
        assert data["full_output"] == "Found the issue."
        assert data["key_findings"] == "Found the issue."
        assert data["confidence"] == 0.9
        assert data["error_message"] is None
        assert data["tokens_consumed"] == 20 * 100
        assert len(data["mission_annotations"]) == 1
        assert data["mission_annotations"][0]["content"] == "Key finding"
        assert data["messages_sent"] == [{"to": "orch", "body": "done"}]
        assert data["duration_seconds"] == 45.0
        assert data["iterations"] == 20

    def test_to_delegation_result_data_failed(self):
        """Failed mission should have status='failed' and confidence=0.0."""
        result = MissionResult(
            agent_id="coder",
            mission_type=MissionGraphType.BUG_FIX,
            success=False,
            result="",
            error="Could not reproduce",
        )

        data = result.to_delegation_result_data()

        assert data["status"] == "failed"
        assert data["confidence"] == 0.0
        assert data["error_message"] == "Could not reproduce"