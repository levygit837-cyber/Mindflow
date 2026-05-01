"""Unit tests for QueryEngine - the unified execution engine."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.engine import QueryEngine
from mindflow_backend.schemas.orchestration.delegation import DelegationTask, DelegationResult
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    Priority,
    SpecialistType,
    ToolScope,
    WorkspacePolicy,
)
from mindflow_backend.schemas.orchestration.workflow import WorkflowStep


class TestQueryEngineInitialization:
    """Test QueryEngine initialization."""

    def test_query_engine_init_minimal(self):
        """Test QueryEngine initialization with minimal parameters."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )
        assert engine is not None

    def test_query_engine_init_with_execution_memory(self):
        """Test QueryEngine initialization with execution memory."""
        mock_execution_memory = MagicMock()
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
            execution_memory=mock_execution_memory,
        )
        assert engine._execution_memory == mock_execution_memory


class TestQueryEngineHelpers:
    """Test QueryEngine helper methods."""

    def test_needs_workspace_isolation_worktree(self):
        """Test workspace isolation detection for WORKTREE policy."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        task = MagicMock()
        task.workspace_policy = "WORKTREE"
        assert engine._needs_workspace_isolation(task) is True

    def test_needs_workspace_isolation_shared(self):
        """Test workspace isolation detection for SHARED policy."""
        from mindflow_backend.schemas.orchestration.orchestrator import WorkspacePolicy

        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        task = MagicMock()
        task.workspace_policy = WorkspacePolicy.SHARED
        assert engine._needs_workspace_isolation(task) is False

    def test_needs_workspace_isolation_with_root_dir(self):
        """Test workspace isolation detection with root_dir."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        task = MagicMock()
        task.workspace_policy = None
        task.root_dir = "/some/path"
        assert engine._needs_workspace_isolation(task) is True

    def test_extract_key_findings_short(self):
        """Test key findings extraction for short responses."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        response = "This is a short response"
        findings = engine._extract_key_findings(response, "")
        assert findings == response

    def test_extract_key_findings_long(self):
        """Test key findings extraction for long responses (truncation)."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        response = "A" * 1500  # Long response
        findings = engine._extract_key_findings(response, "")
        assert len(findings) < 1500
        assert "[truncated" in findings

    def test_extract_files_mentioned(self):
        """Test extraction of file mentions from response."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        response = "The files main.py, app.js, and config.json were modified."
        files = engine._extract_files_mentioned(response)
        assert "main.py" in files
        assert "app.js" in files
        assert "config.json" in files

    def test_extract_symbols_mentioned(self):
        """Test extraction of function/class symbols from response."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        response = "The functions calculate_total() and process_data() were called."
        symbols = engine._extract_symbols_mentioned(response)
        # The regex matches function names with parentheses
        assert "calculate_total(" in symbols
        assert "process_data(" in symbols

    def test_needs_tool_follow_up_true(self):
        """Test tool follow-up detection (insufficient context)."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        response = "não tenho contexto suficiente para responder"
        assert engine._needs_tool_follow_up(response) is True

    def test_needs_tool_follow_up_false(self):
        """Test tool follow-up detection (sufficient context)."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        response = "The answer is 42 based on the provided context."
        assert engine._needs_tool_follow_up(response) is False


class TestWorkflowStepConversion:
    """Test WorkflowStep to DelegationTask conversion."""

    def test_workflow_step_to_delegation_task_basic(self):
        """Test basic conversion of WorkflowStep to DelegationTask."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        step = WorkflowStep(
            step_id="step_1",
            agent_role=AgentType.CODER,
            specialist=SpecialistType.CODER,
            agent_id="coder:coder",
            objective="Implement the login form",
            tools=[ToolScope.FILESYSTEM],
        )

        task = engine._workflow_step_to_delegation_task(
            step=step,
            user_message="Create a login form",
            session_id="test_session",
        )

        assert task.agent == AgentType.CODER
        assert task.specialist == SpecialistType.CODER
        assert task.agent_id == "coder:coder"
        assert task.objective == "Implement the login form"
        assert task.session_id == "test_session"
        assert task.tools == [ToolScope.FILESYSTEM]

    def test_workflow_step_to_delegation_task_with_memory_context(self):
        """Test conversion with memory context."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        step = WorkflowStep(
            step_id="step_1",
            agent_role=AgentType.ANALYST,
            specialist=None,
            agent_id="analyst",
            objective="Analyze the code",
            tools=[],
        )

        task = engine._workflow_step_to_delegation_task(
            step=step,
            user_message="Analyze the code",
            session_id="test_session",
            memory_context="Previous context from memory",
            memory_grounded=True,
        )

        assert task.memory_context == "Previous context from memory"
        assert task.memory_grounded is True

    def test_delegation_result_to_step_output(self):
        """Test conversion of DelegationResult to step output format."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        step = WorkflowStep(
            step_id="step_1",
            agent_role=AgentType.CODER,
            specialist=SpecialistType.CODER,
            agent_id="coder:coder",
            objective="Fix the bug",
            tools=[],
        )

        result = DelegationResult(
            task_id=uuid.uuid4(),
            agent=AgentType.CODER,
            agent_role=AgentType.CODER,
            specialist=SpecialistType.CODER,
            agent_id="coder:coder",
            status="completed",
            key_findings="Bug fixed in line 42",
            full_output="The bug was caused by a null reference. Fixed by adding a null check.",
            confidence=0.9,
            tokens_consumed=1500,
        )

        output = engine._delegation_result_to_step_output(result, step)

        assert output["agent_id"] == "coder:coder"
        assert output["agent_role"] == "coder"
        assert output["specialist"] == "coder"
        assert output["status"] == "completed"
        assert output["key_findings"] == "Bug fixed in line 42"
        assert output["full_output"] == "The bug was caused by a null reference. Fixed by adding a null check."
        assert output["error"] == ""  # Empty string when no error

    def test_delegation_result_to_step_output_with_error(self):
        """Test conversion of failed DelegationResult to step output."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        step = WorkflowStep(
            step_id="step_1",
            agent_role=AgentType.CODER,
            specialist=None,
            agent_id="coder",
            objective="Fix the bug",
            tools=[],
        )

        result = DelegationResult(
            task_id=uuid.uuid4(),
            agent=AgentType.CODER,
            agent_role=AgentType.CODER,
            specialist=None,
            agent_id="coder",
            status="failed",
            key_findings="",
            full_output="",
            error_message="File not found: /path/to/file.py",
            confidence=0.0,
        )

        output = engine._delegation_result_to_step_output(result, step)

        assert output["status"] == "failed"
        assert output["error"] == "File not found: /path/to/file.py"


class TestQueryEngineDelegationTask:
    """Test QueryEngine.delegate_task method."""

    @pytest.mark.asyncio
    async def test_delegate_task_basic(self):
        """Test basic delegation task execution (simplified)."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        # Just test that the method exists and can be called
        # Full execution test would require mocking many internal components
        assert hasattr(engine, "delegate_task")
        assert callable(engine.delegate_task)


class TestQueryEngineExecuteWorkflowStep:
    """Test QueryEngine.execute_workflow_step method."""

    @pytest.mark.asyncio
    async def test_execute_workflow_step_success(self):
        """Test successful execution of a workflow step."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        step = WorkflowStep(
            step_id="step_1",
            agent_role=AgentType.CODER,
            specialist=None,
            agent_id="coder",
            objective="Write a test function",
            tools=[],
        )

        # Mock the delegate_task method
        mock_result = DelegationResult(
            task_id=uuid.uuid4(),
            agent=AgentType.CODER,
            agent_role=AgentType.CODER,
            specialist=None,
            agent_id="coder",
            status="completed",
            key_findings="Test function written",
            full_output="def test_example():\n    assert True",
            confidence=0.9,
            tokens_consumed=500,
        )

        with patch.object(engine, "delegate_task", new_callable=AsyncMock, return_value=mock_result):
            result = await engine.execute_workflow_step(
                step=step,
                user_message="Write a test function",
                provider="openai",
                model="gpt-4",
                session_id="test_session",
            )

        assert result["status"] == "completed"
        assert result["key_findings"] == "Test function written"
        assert result["full_output"] == "def test_example():\n    assert True"

    @pytest.mark.asyncio
    async def test_execute_workflow_step_with_folder_path(self):
        """Test execution with folder_path parameter."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        step = WorkflowStep(
            step_id="step_1",
            agent_role=AgentType.CODER,
            specialist=None,
            agent_id="coder",
            objective="Write code in specific folder",
            tools=[],
        )

        mock_result = DelegationResult(
            task_id=uuid.uuid4(),
            agent=AgentType.CODER,
            agent_role=AgentType.CODER,
            specialist=None,
            agent_id="coder",
            status="completed",
            key_findings="Code written",
            full_output="Code written successfully",
            confidence=0.9,
            tokens_consumed=500,
        )

        with patch.object(engine, "delegate_task", new_callable=AsyncMock, return_value=mock_result) as mock_delegate:
            await engine.execute_workflow_step(
                step=step,
                user_message="Write code in specific folder",
                provider="openai",
                model="gpt-4",
                session_id="test_session",
                folder_path="/tmp/project",
            )

            # Verify that folder_path was passed to the delegation task
            call_args = mock_delegate.call_args
            task = call_args.kwargs["task"]
            assert task.root_dir == "/tmp/project"

    @pytest.mark.asyncio
    async def test_execute_workflow_step_with_memory_context(self):
        """Test execution with memory context."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        step = WorkflowStep(
            step_id="step_1",
            agent_role=AgentType.ANALYST,
            specialist=None,
            agent_id="analyst",
            objective="Analyze with memory context",
            tools=[],
        )

        mock_result = DelegationResult(
            task_id=uuid.uuid4(),
            agent=AgentType.ANALYST,
            agent_role=AgentType.ANALYST,
            specialist=None,
            agent_id="analyst",
            status="completed",
            key_findings="Analysis complete",
            full_output="Based on memory context, the analysis is complete.",
            confidence=0.85,
            tokens_consumed=600,
        )

        with patch.object(engine, "delegate_task", new_callable=AsyncMock, return_value=mock_result) as mock_delegate:
            await engine.execute_workflow_step(
                step=step,
                user_message="Analyze with memory context",
                provider="openai",
                model="gpt-4",
                session_id="test_session",
                memory_context="Previous analysis results",
                memory_grounded=True,
            )

            # Verify that memory context was passed
            call_args = mock_delegate.call_args
            task = call_args.kwargs["task"]
            assert task.memory_context == "Previous analysis results"
            assert task.memory_grounded is True


class TestQueryEngineWorkspaceResolution:
    """Test QueryEngine workspace resolution methods."""

    def test_needs_workspace_isolation_worktree(self):
        """Test workspace isolation detection for WORKTREE policy."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        task = MagicMock()
        task.workspace_policy = WorkspacePolicy.WORKTREE
        assert engine._needs_workspace_isolation(task) is True

    def test_needs_workspace_isolation_auto(self):
        """Test workspace isolation detection for AUTO policy."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        task = MagicMock()
        task.workspace_policy = WorkspacePolicy.AUTO
        task.root_dir = "/some/path"
        assert engine._needs_workspace_isolation(task) is True

    def test_needs_workspace_isolation_auto_no_root_dir(self):
        """Test workspace isolation detection for AUTO policy without root_dir."""
        engine = QueryEngine(
            providers=[],
            budget=TokenBudget(max_tokens=100_000),
            session_id="test_session",
            use_file_cache=False,
        )

        task = MagicMock()
        task.workspace_policy = WorkspacePolicy.AUTO
        task.root_dir = None
        assert engine._needs_workspace_isolation(task) is False
