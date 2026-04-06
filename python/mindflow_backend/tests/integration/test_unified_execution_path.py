"""Tests for unified execution path migration.

Tests validate that QueryEngine correctly handles WorkflowStep → DelegationTask
conversion and DelegationResult → step output conversion.
"""

import uuid
import pytest
from unittest.mock import MagicMock

from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.engine import QueryEngine
from mindflow_backend.schemas.orchestration.delegation import DelegationResult, DelegationStatus
from mindflow_backend.schemas.orchestration.orchestrator import AgentType, SpecialistType
from mindflow_backend.schemas.orchestration.workflow import WorkflowStep


class TestWorkflowStepToDelegationTask:
    """Tests for WorkflowStep → DelegationTask conversion."""

    def setup_method(self):
        """Setup QueryEngine instance for tests."""
        self.engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

    def test_basic_conversion(self):
        """Test basic conversion of WorkflowStep to DelegationTask."""
        step = WorkflowStep(
            step_id="step-1",
            agent_id="coder",
            agent_role=AgentType.CODER,
            specialist=SpecialistType.CODER,
            objective="Implement feature X",
        )

        task = self.engine._workflow_step_to_delegation_task(
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

        task = self.engine._workflow_step_to_delegation_task(
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

        task = self.engine._workflow_step_to_delegation_task(
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

        task = self.engine._workflow_step_to_delegation_task(
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

        task = self.engine._workflow_step_to_delegation_task(
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

        task = self.engine._workflow_step_to_delegation_task(
            step=step,
            user_message="Write code",
            session_id="test-session",
            max_iterations=10,
        )

        assert task.max_iterations == 10


class TestDelegationResultToStepOutput:
    """Tests for DelegationResult → step output conversion."""

    def setup_method(self):
        """Setup QueryEngine instance for tests."""
        self.engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

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
            task_id=uuid.uuid4(),
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

        output = self.engine._delegation_result_to_step_output(result, step)

        assert output["agent_id"] == "coder"
        assert output["agent_role"] == "coder"
        assert output["specialist"] == "coder"
        assert output["status"] == "completed"
        assert output["key_findings"] == "Code written successfully"
        assert output["full_output"] == "Full implementation details..."
        assert output["error"] == ""  # error_message defaults to ""
