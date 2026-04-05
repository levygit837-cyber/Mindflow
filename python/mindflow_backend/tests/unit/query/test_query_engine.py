"""Unit tests for QueryEngine - the unified execution engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.engine import QueryEngine


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
        # The regex matches file extensions, not filenames
        assert "py" in files
        assert "js" in files
        assert "json" in files

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
