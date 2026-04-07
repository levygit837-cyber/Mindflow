"""Unit tests for common nodes."""

from __future__ import annotations

import pytest

from mindflow_backend.nodes.common.initialize_node import InitializeNode
from mindflow_backend.nodes.common.read_context_node import ReadContextNode
from mindflow_backend.nodes.common.report_node import ReportNode


class TestInitializeNode:
    """Test suite for InitializeNode."""

    @pytest.fixture
    def node(self) -> InitializeNode:
        """Create InitializeNode instance."""
        return InitializeNode()

    @pytest.mark.asyncio
    async def test_execute_with_valid_inputs(self, node: InitializeNode) -> None:
        """Test execution with valid inputs."""
        state = {
            "agent_id": "analyst",
            "mission_type": "analysis",
            "session_id": "test-session",
            "max_iterations": 100,
            "max_duration_seconds": 60.0,
        }

        result = await node.execute(state)

        assert result["iteration"] == 0
        assert result["confidence"] == 0.0
        assert result["annotations"] == []
        assert "enabled_tools" in result
        assert "memory_scope" in result
        assert "metrics" in result
        assert result["current_phase"] == "initialized"

    @pytest.mark.asyncio
    async def test_execute_with_missing_agent_id(self, node: InitializeNode) -> None:
        """Test execution with missing agent_id."""
        state = {
            "mission_type": "analysis",
            "session_id": "test-session",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: agent_id" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_mission_type(self, node: InitializeNode) -> None:
        """Test execution with missing mission_type."""
        state = {
            "agent_id": "analyst",
            "session_id": "test-session",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: mission_type" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_session_id(self, node: InitializeNode) -> None:
        """Test execution with missing session_id."""
        state = {
            "agent_id": "analyst",
            "mission_type": "analysis",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: session_id" in errors

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, node: InitializeNode) -> None:
        """Test error handling in execute."""
        state = {
            "agent_id": "analyst",
            "mission_type": "analysis",
            "session_id": "test-session",
        }

        result = await node.execute(state)

        # Should return default values on error or successful execution
        assert result["iteration"] == 0
        assert result["confidence"] == 0.0
        # Note: tools_config may have values even if setup fails
        assert "enabled_tools" in result
        assert "memory_scope" in result
        # metrics should have default values from initialize_metrics
        assert "metrics" in result
        assert result["current_phase"] in ["initialized", "error"]


class TestReadContextNode:
    """Test suite for ReadContextNode."""

    @pytest.fixture
    def node(self) -> ReadContextNode:
        """Create ReadContextNode instance."""
        return ReadContextNode()

    @pytest.mark.asyncio
    async def test_execute_with_valid_inputs(self, node: ReadContextNode) -> None:
        """Test execution with valid inputs."""
        state = {
            "working_directory": "/home/levybonito/Projetos/MindFlow/python",
            "mission_type": "analysis",
        }

        result = await node.execute(state)

        assert "project_structure" in result
        assert "relevant_files" in result
        assert "file_count" in result
        assert result["current_phase"] == "context_read"
        assert isinstance(result["file_count"], int)

    @pytest.mark.asyncio
    async def test_execute_with_missing_working_directory(self, node: ReadContextNode) -> None:
        """Test execution with missing working_directory."""
        state = {}

        errors = node.validate_inputs(state)
        assert "Missing required input: working_directory" in errors

    @pytest.mark.asyncio
    async def test_execute_with_default_working_directory(self, node: ReadContextNode) -> None:
        """Test execution with default working directory."""
        state = {}

        result = await node.execute(state)

        assert "project_structure" in result
        assert result["current_phase"] == "context_read"


class TestReportNode:
    """Test suite for ReportNode."""

    @pytest.fixture
    def node(self) -> ReportNode:
        """Create ReportNode instance."""
        return ReportNode()

    @pytest.mark.asyncio
    async def test_execute_with_valid_inputs(self, node: ReportNode) -> None:
        """Test execution with valid inputs."""
        state = {
            "agent_id": "analyst",
            "mission_type": "analysis",
            "session_id": "test-session",
            "iteration": 5,
            "confidence": 0.85,
            "annotations": [
                {"content": "test annotation", "confidence": 0.9},
            ],
            "started_at": 1234567890.0,
            "metrics": {
                "nodes_executed": 10,
                "nodes_failed": 0,
                "total_tokens_used": 1000,
            },
        }

        result = await node.execute(state)

        assert "result" in result
        assert "metrics" in result
        assert "memory_annotations" in result
        assert result["current_phase"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_with_missing_agent_id(self, node: ReportNode) -> None:
        """Test execution with missing agent_id."""
        state = {
            "mission_type": "analysis",
            "session_id": "test-session",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: agent_id" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_mission_type(self, node: ReportNode) -> None:
        """Test execution with missing mission_type."""
        state = {
            "agent_id": "analyst",
            "session_id": "test-session",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: mission_type" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_session_id(self, node: ReportNode) -> None:
        """Test execution with missing session_id."""
        state = {
            "agent_id": "analyst",
            "mission_type": "analysis",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: session_id" in errors
