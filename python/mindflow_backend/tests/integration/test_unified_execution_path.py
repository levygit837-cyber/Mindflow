"""Tests for unified execution path migration.

Tests validate that step_runner correctly uses DelegationEngine as backend
and that the integration maintains backward compatibility.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from mindflow_backend.orchestrator.delegation.converter import (
    delegation_result_to_step_output,
    workflow_step_to_delegation_task,
)
from mindflow_backend.schemas.orchestration.delegation import DelegationResult, DelegationStatus
from mindflow_backend.schemas.orchestration.orchestrator import AgentType, SpecialistType
from mindflow_backend.schemas.orchestration.workflow import WorkflowStep


class TestWorkflowStepToDelegationTask:
    """Tests for WorkflowStep → DelegationTask conversion."""

    def test_basic_conversion(self):
        """Test basic conversion of WorkflowStep to DelegationTask."""
        step = WorkflowStep(
            step_id="step-1",
            agent_id="coder",
            agent_role=AgentType.CODER,
            specialist=SpecialistType.CODER,
            objective="Implement feature X",
        )

        task = workflow_step_to_delegation_task(
            step=step,
            user_message="Implement feature X",
            session_id="test-session",
        )

        assert task.agent == AgentType.CODER
        assert task.agent_role == AgentType.CODER
        assert task.specialist == SpecialistType.CODER
        assert task.agent_id == "coder"
        assert task.objective == "Implement feature X"
        assert task.session_id == "test-session"

    def test_conversion_with_memory_context(self):
        """Test conversion with memory context."""
        step = WorkflowStep(
            step_id="step-1",
            agent_id="analyst",
            agent_role=AgentType.ANALYST,
            objective="Analyze code",
        )

        task = workflow_step_to_delegation_task(
            step=step,
            user_message="Analyze code",
            session_id="test-session",
            memory_context="Previous analysis results...",
            memory_grounded=True,
        )

        assert task.memory_context == "Previous analysis results..."
        assert task.memory_grounded is True

    def test_conversion_with_conversation_history(self):
        """Test conversion with conversation history."""
        step = WorkflowStep(
            step_id="step-1",
            agent_id="coder",
            agent_role=AgentType.CODER,
            objective="Write code",
        )

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        task = workflow_step_to_delegation_task(
            step=step,
            user_message="Write code",
            session_id="test-session",
            conversation_history=history,
        )

        assert task.conversation_history == history

    def test_conversion_with_prior_context(self):
        """Test conversion with prior context."""
        step = WorkflowStep(
            step_id="step-1",
            agent_id="coder",
            agent_role=AgentType.CODER,
            objective="Continue work",
        )

        task = workflow_step_to_delegation_task(
            step=step,
            user_message="Continue work",
            session_id="test-session",
            prior_context="Previous step output...",
        )

        assert task.context_from_session == "Previous step output..."

    def test_conversion_with_folder_path(self):
        """Test conversion with folder path."""
        step = WorkflowStep(
            step_id="step-1",
            agent_id="coder",
            agent_role=AgentType.CODER,
            objective="Write code",
        )

        task = workflow_step_to_delegation_task(
            step=step,
            user_message="Write code",
            session_id="test-session",
            folder_path="/path/to/project",
        )

        assert task.root_dir == "/path/to/project"

    def test_conversion_with_max_iterations(self):
        """Test conversion with max iterations."""
        step = WorkflowStep(
            step_id="step-1",
            agent_id="coder",
            agent_role=AgentType.CODER,
            objective="Write code",
        )

        task = workflow_step_to_delegation_task(
            step=step,
            user_message="Write code",
            session_id="test-session",
            max_iterations=10,
        )

        assert task.max_iterations == 10


class TestDelegationResultToStepOutput:
    """Tests for DelegationResult → step_runner output conversion."""

    def test_basic_conversion(self):
        """Test basic conversion of DelegationResult to step output."""
        step = WorkflowStep(
            step_id="step-1",
            agent_id="coder",
            agent_role=AgentType.CODER,
            specialist=SpecialistType.CODER,
            objective="Write code",
        )

        result = DelegationResult(
            task_id=uuid4(),
            agent=AgentType.CODER,
            agent_role=AgentType.CODER,
            specialist=SpecialistType.CODER,
            agent_id="coder",
            status=DelegationStatus.COMPLETED,
            key_findings="Code written successfully",
            full_output="Full implementation details...",
            files_analyzed=[],
            symbols_found=[],
            gaps_detected=[],
            confidence=0.9,
            tokens_consumed=100,
        )

        output = delegation_result_to_step_output(result, step)

        assert output["agent_id"] == "coder"
        assert output["agent_role"] == "coder"
        assert output["specialist"] == "coder"
        assert output["status"] == "completed"
        assert output["key_findings"] == "Code written successfully"
        assert output["full_output"] == "Full implementation details..."
        assert output["error"] == ""  # error_message defaults to ""


class TestDelegationEngineMemoryGrounded:
    """Tests for DelegationEngine memory-grounded functionality."""

    def test_needs_tool_follow_up_positive(self):
        """Test _needs_tool_follow_up with insufficient context markers."""
        from mindflow_backend.orchestrator.delegation.engine import DelegationEngine

        engine = DelegationEngine()

        # Should return True for insufficient context
        assert engine._needs_tool_follow_up("não tenho contexto suficiente")
        assert engine._needs_tool_follow_up("preciso investigar")
        assert engine._needs_tool_follow_up("insufficient context")
        assert engine._needs_tool_follow_up("need to inspect")

    def test_needs_tool_follow_up_negative(self):
        """Test _needs_tool_follow_up with sufficient context."""
        from mindflow_backend.orchestrator.delegation.engine import DelegationEngine

        engine = DelegationEngine()

        # Should return False for sufficient context
        assert not engine._needs_tool_follow_up("Here is the answer you need")
        assert not engine._needs_tool_follow_up("The analysis shows X")
        assert not engine._needs_tool_follow_up("Based on the context provided")

    def test_needs_tool_follow_up_empty(self):
        """Test _needs_tool_follow_up with empty response."""
        from mindflow_backend.orchestrator.delegation.engine import DelegationEngine

        engine = DelegationEngine()

        # Should return True for empty response
        assert engine._needs_tool_follow_up("")
        assert engine._needs_tool_follow_up("   ")
