"""Unit tests for analysis nodes."""

from __future__ import annotations

import pytest

from mindflow_backend.nodes.analysis.investigate_node import InvestigateNode
from mindflow_backend.nodes.analysis.annotate_node import AnnotateNode
from mindflow_backend.nodes.analysis.synthesize_node import SynthesizeNode


class TestInvestigateNode:
    """Test suite for InvestigateNode."""

    @pytest.fixture
    def node(self) -> InvestigateNode:
        """Create InvestigateNode instance."""
        return InvestigateNode()

    @pytest.mark.asyncio
    async def test_execute_with_valid_inputs(self, node: InvestigateNode) -> None:
        """Test execution with valid inputs."""
        state = {
            "relevant_files": [
                "mindflow_backend/nodes/common/initialize_node.py",
            ],
            "working_directory": "/home/levybonito/Projetos/MindFlow/python",
            "agent_id": "analyst",
            "symbol_to_trace": "BaseNode",
        }

        result = await node.execute(state)

        assert "findings" in result
        assert "patterns_found" in result
        assert "dependencies" in result
        assert "structure" in result
        assert result["current_phase"] == "investigating"

    @pytest.mark.asyncio
    async def test_execute_with_default_symbol(self, node: InvestigateNode) -> None:
        """Test execution with default symbol to trace."""
        state = {
            "relevant_files": [],
            "working_directory": "/home/levybonito/Projetos/MindFlow/python",
            "agent_id": "analyst",
        }

        result = await node.execute(state)

        assert "dependencies" in result
        # Should use default symbol "BaseNode"

    @pytest.mark.asyncio
    async def test_execute_with_missing_relevant_files(self, node: InvestigateNode) -> None:
        """Test execution with missing relevant_files."""
        state = {
            "working_directory": "/home/levybonito/Projetos/MindFlow/python",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: relevant_files" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_working_directory(self, node: InvestigateNode) -> None:
        """Test execution with missing working_directory."""
        state = {
            "relevant_files": [],
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: working_directory" in errors


class TestAnnotateNode:
    """Test suite for AnnotateNode."""

    @pytest.fixture
    def node(self) -> AnnotateNode:
        """Create AnnotateNode instance."""
        return AnnotateNode()

    @pytest.mark.asyncio
    async def test_execute_with_valid_inputs(self, node: AnnotateNode) -> None:
        """Test execution with valid inputs."""
        state = {
            "findings": {
                "key_findings": ["test finding"],
            },
            "agent_id": "analyst",
            "mission_type": "analysis",
            "session_id": "test-session",
            "iteration": 1,
            "confidence": 0.5,
            "annotations": [],
        }

        result = await node.execute(state)

        assert "annotations" in result
        assert "confidence" in result
        assert result["confidence"] >= state["confidence"]  # Confidence should increase
        assert result["current_phase"] == "annotated"

    @pytest.mark.asyncio
    async def test_execute_with_missing_findings(self, node: AnnotateNode) -> None:
        """Test execution with missing findings."""
        state = {
            "agent_id": "analyst",
            "mission_type": "analysis",
            "session_id": "test-session",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: findings" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_agent_id(self, node: AnnotateNode) -> None:
        """Test execution with missing agent_id."""
        state = {
            "findings": {},
            "mission_type": "analysis",
            "session_id": "test-session",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: agent_id" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_mission_type(self, node: AnnotateNode) -> None:
        """Test execution with missing mission_type."""
        state = {
            "findings": {},
            "agent_id": "analyst",
            "session_id": "test-session",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: mission_type" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_session_id(self, node: AnnotateNode) -> None:
        """Test execution with missing session_id."""
        state = {
            "findings": {},
            "agent_id": "analyst",
            "mission_type": "analysis",
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: session_id" in errors


class TestSynthesizeNode:
    """Test suite for SynthesizeNode."""

    @pytest.fixture
    def node(self) -> SynthesizeNode:
        """Create SynthesizeNode instance."""
        return SynthesizeNode()

    @pytest.mark.asyncio
    async def test_execute_with_valid_inputs(self, node: SynthesizeNode) -> None:
        """Test execution with valid inputs."""
        state = {
            "annotations": [
                {
                    "content": "test annotation 1",
                    "confidence": 0.8,
                    "type": "pattern_match",
                },
                {
                    "content": "test annotation 2",
                    "confidence": 0.9,
                    "type": "dependency",
                },
            ],
            "confidence": 0.85,
        }

        result = await node.execute(state)

        assert "synthesis" in result
        assert "themes" in result
        assert "narrative" in result
        assert result["current_phase"] == "synthesized"
        assert isinstance(result["themes"], list)
        assert isinstance(result["narrative"], str)

    @pytest.mark.asyncio
    async def test_execute_with_empty_annotations(self, node: SynthesizeNode) -> None:
        """Test execution with empty annotations."""
        state = {
            "annotations": [],
            "confidence": 0.0,
        }

        result = await node.execute(state)

        assert "synthesis" in result
        assert "themes" in result
        assert "narrative" in result

    @pytest.mark.asyncio
    async def test_execute_with_missing_annotations(self, node: SynthesizeNode) -> None:
        """Test execution with missing annotations."""
        state = {
            "confidence": 0.85,
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: annotations" in errors

    @pytest.mark.asyncio
    async def test_execute_with_missing_confidence(self, node: SynthesizeNode) -> None:
        """Test execution with missing confidence."""
        state = {
            "annotations": [],
        }

        errors = node.validate_inputs(state)
        assert "Missing required input: confidence" in errors
