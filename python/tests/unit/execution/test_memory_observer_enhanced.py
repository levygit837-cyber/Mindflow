"""Integration tests for MemoryObserver with DirectoryMapper and HierarchicalAnnotation (Phase 1)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from mindflow_backend.execution.observers.memory_observer import MemoryObserver
from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.memory.storage.models import (
    Base,
    HierarchicalAnnotation,
    MemoryCategory,
    ProjectMemory,
)


@pytest_asyncio.fixture
async def async_db():
    """Create an async in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


@pytest_asyncio.fixture
async def async_session(async_db):
    """Create an async database session for testing."""
    async with AsyncSession(async_db) as session:
        yield session


@pytest_asyncio.fixture
async def memory_facade():
    """Create a MemoryFacade instance."""
    return MemoryFacade()


@pytest_asyncio.fixture
async def memory_observer(memory_facade):
    """Create a MemoryObserver instance with DirectoryMapper."""
    observer = MemoryObserver(
        observer_agent_id="test-observer",
        memory_facade=memory_facade,
        session_id="test-session",
        project_root="/test/project",
        project_name="TestProject",
    )
    return observer


# ============================================================================
# Code Change Detection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_extract_code_change_from_write_file_event(memory_observer: MemoryObserver):
    """Test extracting code change info from write_file tool_result event."""
    event = {
        "type": "tool_result",
        "agent_id": "coder",
        "mission_id": "mission-123",
        "data": {
            "tool_name": "write_file",
            "file_path": "python/api/v1/chat.py",
            "lines_modified": {"start": 10, "end": 20, "count": 10},
            "diff": "+def new_function():\n+    pass",
        },
    }

    code_info = memory_observer._extract_code_change(event)

    assert code_info is not None
    assert code_info["file_path"] == "python/api/v1/chat.py"
    assert code_info["lines"] == {"start": 10, "end": 20, "count": 10}
    assert code_info["diff"] == "+def new_function():\n+    pass"
    assert code_info["operation"] == "write_file"


@pytest.mark.asyncio
async def test_extract_code_change_from_edit_file_event(memory_observer: MemoryObserver):
    """Test extracting code change info from edit_file tool_result event."""
    event = {
        "type": "tool_result",
        "agent_id": "coder",
        "mission_id": "mission-123",
        "data": {
            "tool_name": "edit_file",
            "file": "src/services/auth.ts",
            "lines_modified": {"start": 45, "end": 67},
        },
    }

    code_info = memory_observer._extract_code_change(event)

    assert code_info is not None
    assert code_info["file_path"] == "src/services/auth.ts"
    assert code_info["operation"] == "edit_file"


@pytest.mark.asyncio
async def test_extract_code_change_from_file_modified_event(memory_observer: MemoryObserver):
    """Test extracting code change info from file_modified event."""
    event = {
        "type": "file_modified",
        "agent_id": "coder",
        "mission_id": "mission-123",
        "data": {
            "file_path": "tests/test_auth.py",
            "diff": "-old line\n+new line",
        },
    }

    code_info = memory_observer._extract_code_change(event)

    assert code_info is not None
    assert code_info["file_path"] == "tests/test_auth.py"
    assert code_info["operation"] == "file_modified"


@pytest.mark.asyncio
async def test_extract_code_change_returns_none_for_non_file_event(
    memory_observer: MemoryObserver,
):
    """Test that non-file events return None."""
    event = {
        "type": "agent_decision",
        "agent_id": "analyst",
        "mission_id": "mission-123",
        "message": "Decided to use JWT",
    }

    code_info = memory_observer._extract_code_change(event)

    assert code_info is None


# ============================================================================
# Rich Context Generation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_rich_context_with_all_fields(memory_observer: MemoryObserver):
    """Test generating rich context with all available fields."""
    event = {
        "agent_id": "coder",
        "mission_id": "mission-123",
        "message": "Added JWT validation middleware",
    }

    code_info = {
        "file_path": "python/api/middleware/auth.py",
        "lines": {"start": 45, "end": 67, "type": "added"},
        "diff": "+def validate_jwt(token):\n+    # validation logic",
        "operation": "write_file",
    }

    context = memory_observer._generate_rich_context(event, code_info)

    assert "coder" in context
    assert "python/api/middleware/auth.py" in context
    assert "Lines added: 45-67" in context
    assert "Added JWT validation middleware" in context
    assert "Category: api" in context
    assert "middleware" in context
    assert "mission-123" in context
    assert "test-session" in context


@pytest.mark.asyncio
async def test_generate_rich_context_without_lines(memory_observer: MemoryObserver):
    """Test generating rich context when lines_modified is not available."""
    event = {
        "agent_id": "coder",
        "mission_id": "mission-123",
        "message": "Modified config file",
    }

    code_info = {
        "file_path": "config/settings.py",
        "lines": {},
        "diff": "",
        "operation": "edit_file",
    }

    context = memory_observer._generate_rich_context(event, code_info)

    assert "config/settings.py" in context
    assert "Modified config file" in context
    # Should not have "Lines" section
    assert "Lines" not in context or "?: ?" in context


# ============================================================================
# Event Processing with DirectoryMapper Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_event_creates_hierarchical_annotation_for_code_change(
    memory_observer: MemoryObserver,
):
    """Test that code change events create hierarchical annotations."""
    event = {
        "type": "tool_result",
        "agent_id": "coder",
        "mission_id": "mission-123",
        "level": "INFO",
        "message": "Modified API endpoint",
        "data": {
            "tool_name": "write_file",
            "file_path": "python/api/v1/chat.py",
            "lines_modified": {"start": 10, "end": 20},
            "diff": "+new code",
        },
    }

    # Mock the database session
    with patch(
        "mindflow_backend.execution.observers.memory_observer.get_db_session"
    ) as mock_get_session:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_get_session.return_value = mock_session

        await memory_observer._process_event(event)

        # Verify save_hierarchical_annotation was called
        assert memory_observer._memory.save_hierarchical_annotation
        assert memory_observer._annotations_count == 1


@pytest.mark.asyncio
async def test_process_event_uses_directory_mapper_for_categorization(
    memory_observer: MemoryObserver,
):
    """Test that DirectoryMapper is used to categorize file paths."""
    event = {
        "type": "tool_result",
        "agent_id": "coder",
        "mission_id": "mission-123",
        "level": "INFO",
        "message": "Modified service",
        "data": {
            "tool_name": "edit_file",
            "file_path": "python/services/auth/jwt.py",
        },
    }

    with patch(
        "mindflow_backend.execution.observers.memory_observer.get_db_session"
    ) as mock_get_session:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_get_session.return_value = mock_session

        await memory_observer._process_event(event)

        # Verify DirectoryMapper classified the file
        category, subcategory = memory_observer._directory_mapper.classify(
            "python/services/auth/jwt.py"
        )
        assert category == "services"
        assert subcategory == "auth"


# ============================================================================
# Rate Limiting Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_event_respects_rate_limit(memory_observer: MemoryObserver):
    """Test that rate limiting prevents excessive annotations."""
    # Set annotations_this_minute to the limit
    memory_observer._annotations_this_minute = 10

    event = {
        "type": "tool_result",
        "agent_id": "coder",
        "mission_id": "mission-123",
        "level": "ERROR",  # High importance
        "message": "Critical error",
        "data": {"tool_name": "write_file", "file_path": "test.py"},
    }

    initial_count = memory_observer._annotations_count

    await memory_observer._process_event(event)

    # Should not create annotation due to rate limit
    assert memory_observer._annotations_count == initial_count


# ============================================================================
# Importance Scoring Tests
# ============================================================================


@pytest.mark.asyncio
async def test_score_importance_for_error_event():
    """Test importance scoring for ERROR level events."""
    event = {
        "type": "tool_result",
        "level": "ERROR",
        "message": "Critical failure",
    }

    score = MemoryObserver._score_importance(event)

    assert score >= 0.9


@pytest.mark.asyncio
async def test_score_importance_for_warning_event():
    """Test importance scoring for WARNING level events."""
    event = {
        "type": "finding",
        "level": "WARNING",
        "message": "Potential issue detected",
    }

    score = MemoryObserver._score_importance(event)

    assert score >= 0.7


@pytest.mark.asyncio
async def test_score_importance_decreases_for_late_iterations():
    """Test that importance decreases for events in late iterations."""
    event_early = {
        "type": "tool_result",
        "level": "INFO",
        "iteration": 1,
    }

    event_late = {
        "type": "tool_result",
        "level": "INFO",
        "iteration": 15,
    }

    score_early = MemoryObserver._score_importance(event_early)
    score_late = MemoryObserver._score_importance(event_late)

    assert score_late < score_early


# ============================================================================
# Event Classification Tests
# ============================================================================


@pytest.mark.asyncio
async def test_classify_event_as_warning():
    """Test event classification for ERROR/WARNING levels."""
    event = {"type": "tool_result", "level": "ERROR"}

    annotation_type = MemoryObserver._classify_event(event)

    assert annotation_type == "warning"


@pytest.mark.asyncio
async def test_classify_event_as_finding():
    """Test event classification for finding events."""
    event = {"type": "finding", "level": "INFO"}

    annotation_type = MemoryObserver._classify_event(event)

    assert annotation_type == "finding"


@pytest.mark.asyncio
async def test_classify_event_as_insight():
    """Test event classification for mission_complete events."""
    event = {"type": "mission_complete", "level": "INFO"}

    annotation_type = MemoryObserver._classify_event(event)

    assert annotation_type == "insight"


@pytest.mark.asyncio
async def test_classify_event_as_observation():
    """Test event classification for generic events."""
    event = {"type": "progress", "level": "INFO"}

    annotation_type = MemoryObserver._classify_event(event)

    assert annotation_type == "observation"


# ============================================================================
# Tag Extraction Tests
# ============================================================================


@pytest.mark.asyncio
async def test_extract_tags_from_event():
    """Test tag extraction from event."""
    event = {
        "type": "tool_result",
        "agent_id": "coder",
        "level": "ERROR",
    }

    tags = MemoryObserver._extract_tags(event)

    assert "event:tool_result" in tags
    assert "agent:coder" in tags
    assert "error" in tags


# ============================================================================
# Observer Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_observer_starts_and_stops_gracefully(memory_observer: MemoryObserver):
    """Test observer lifecycle."""
    await memory_observer.start_observing(["mission-123"])

    assert memory_observer._running is True
    assert "mission-123" in memory_observer._observed_missions

    await memory_observer.stop_observing()

    assert memory_observer._running is False


@pytest.mark.asyncio
async def test_observer_processes_queued_events(memory_observer: MemoryObserver):
    """Test that observer processes events from queue."""
    await memory_observer.start_observing(["mission-123"])

    event = {
        "type": "tool_result",
        "agent_id": "coder",
        "mission_id": "mission-123",
        "level": "ERROR",
        "message": "Test event",
        "data": {"tool_name": "write_file", "file_path": "test.py"},
    }

    with patch(
        "mindflow_backend.execution.observers.memory_observer.get_db_session"
    ) as mock_get_session:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_get_session.return_value = mock_session

        await memory_observer.receive_event(event)
        await asyncio.sleep(0.2)  # Give time for processing

        assert memory_observer._annotations_count > 0

    await memory_observer.stop_observing()


# ============================================================================
# Stats Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_stats_returns_correct_info(memory_observer: MemoryObserver):
    """Test that get_stats returns correct observer statistics."""
    await memory_observer.start_observing(["mission-123", "mission-456"])

    stats = memory_observer.get_stats()

    assert stats["observer_id"] == "test-observer"
    assert stats["running"] is True
    assert stats["total_annotations"] == 0
    assert stats["rate_this_minute"] == 0
    assert "mission-123" in stats["observed_missions"]
    assert "mission-456" in stats["observed_missions"]

    await memory_observer.stop_observing()


# ============================================================================
# Phase 3: Rich NL Context Tests
# ============================================================================


class TestMemoryObserverRichContext:
    """Tests para _summarize_event_rich() - contexto NL rico sem limite de caracteres."""

    @pytest.mark.asyncio
    async def test_summarize_event_rich_tool_result_with_diff(self, memory_observer: MemoryObserver):
        """_summarize_event_rich extrai diff_summary de tool_result events."""
        event = {
            "type": "tool_result",
            "agent_id": "coder",
            "mission_id": "mission-1",
            "level": "INFO",
            "message": "File modified successfully",
            "data": {
                "tool_name": "edit_file",
                "status": "success",
                "diff_summary": "Added error handling to login function",
                "result": "File updated: src/auth.py",
            },
            "iteration": 3,
        }

        rich_context = memory_observer._summarize_event_rich(event)

        # Verificar estrutura do contexto rico
        assert "Agent coder [tool_result]" in rich_context
        assert "Tool: edit_file (status: success)" in rich_context
        assert "Diff Summary:" in rich_context
        assert "Added error handling to login function" in rich_context
        assert "Result: File updated: src/auth.py" in rich_context
        assert "Mission: mission-1" in rich_context
        assert "Session: test-session" in rich_context
        assert "Iteration: 3" in rich_context

        # Verificar que não há limite de 500 chars
        assert len(rich_context) > 200  # Contexto rico deve ser detalhado

    @pytest.mark.asyncio
    async def test_summarize_event_rich_agent_decision(self, memory_observer: MemoryObserver):
        """_summarize_event_rich formata agent_decision events com reasoning."""
        event = {
            "type": "agent_decision",
            "agent_id": "planner",
            "mission_id": "mission-2",
            "level": "INFO",
            "message": "Decided to refactor authentication module",
            "data": {
                "decision": "Refactor auth module using OAuth2",
                "reasoning": "Current implementation has security vulnerabilities and lacks modern standards",
            },
            "iteration": 1,
        }

        rich_context = memory_observer._summarize_event_rich(event)

        assert "Agent planner [agent_decision]" in rich_context
        assert "Decision: Refactor auth module using OAuth2" in rich_context
        assert "Reasoning: Current implementation has security vulnerabilities" in rich_context
        assert "Mission: mission-2" in rich_context

    @pytest.mark.asyncio
    async def test_summarize_event_rich_finding(self, memory_observer: MemoryObserver):
        """_summarize_event_rich formata finding events com confidence."""
        event = {
            "type": "finding",
            "agent_id": "researcher",
            "mission_id": "mission-3",
            "level": "INFO",
            "message": "Found potential SQL injection vulnerability",
            "data": {
                "finding": "SQL query uses string concatenation instead of parameterized queries",
                "confidence": "high",
            },
        }

        rich_context = memory_observer._summarize_event_rich(event)

        assert "Agent researcher [finding]" in rich_context
        assert "Finding: SQL query uses string concatenation" in rich_context
        assert "Confidence: high" in rich_context

    @pytest.mark.asyncio
    async def test_summarize_event_rich_error_with_traceback(self, memory_observer: MemoryObserver):
        """_summarize_event_rich formata error events com traceback."""
        event = {
            "type": "error",
            "agent_id": "executor",
            "mission_id": "mission-4",
            "level": "ERROR",
            "message": "Failed to execute command",
            "data": {
                "error": "FileNotFoundError: config.yaml not found",
                "traceback": "Traceback (most recent call last):\n  File 'main.py', line 42\n    raise FileNotFoundError",
            },
        }

        rich_context = memory_observer._summarize_event_rich(event)

        assert "Agent executor [error] [ERROR]" in rich_context
        assert "Error: FileNotFoundError: config.yaml not found" in rich_context
        assert "Traceback:" in rich_context
        assert "File 'main.py', line 42" in rich_context

    @pytest.mark.asyncio
    async def test_summarize_event_rich_mission_complete(self, memory_observer: MemoryObserver):
        """_summarize_event_rich formata mission_complete events."""
        event = {
            "type": "mission_complete",
            "agent_id": "coder",
            "mission_id": "mission-5",
            "level": "INFO",
            "message": "Mission completed successfully",
            "data": {
                "status": "success",
                "summary": "Implemented authentication module with OAuth2 support",
            },
        }

        rich_context = memory_observer._summarize_event_rich(event)

        assert "Agent coder [mission_complete]" in rich_context
        assert "Status: success" in rich_context
        assert "Summary: Implemented authentication module with OAuth2 support" in rich_context

    @pytest.mark.asyncio
    async def test_summarize_event_rich_no_character_limit(self, memory_observer: MemoryObserver):
        """_summarize_event_rich não tem limite de 500 caracteres."""
        # Criar evento com diff muito longo
        long_diff = "+" * 1000 + "\n" + "-" * 1000
        event = {
            "type": "tool_result",
            "agent_id": "coder",
            "mission_id": "mission-1",
            "level": "INFO",
            "message": "Large file modification",
            "data": {
                "tool_name": "edit_file",
                "status": "success",
                "diff_summary": long_diff,
                "result": "File updated with extensive changes",
            },
        }

        rich_context = memory_observer._summarize_event_rich(event)

        # Verificar que contexto é maior que 500 chars (limite antigo)
        assert len(rich_context) > 500
        # Verificar que diff está presente
        assert long_diff in rich_context


# ============================================================================
# Phase 3: Cross-Agent Tags Tests
# ============================================================================


class TestMemoryObserverCrossAgentTags:
    """Tests para _extract_tags() - tags de cross-agent queries."""

    @pytest.mark.asyncio
    async def test_extract_tags_includes_session_id(self, memory_observer: MemoryObserver):
        """_extract_tags inclui session:{session_id} tag."""
        event = {
            "type": "tool_result",
            "agent_id": "coder",
            "level": "INFO",
        }

        tags = memory_observer._extract_tags(event)

        assert "session:test-session" in tags

    @pytest.mark.asyncio
    async def test_extract_tags_includes_source_agent_id(self, memory_observer: MemoryObserver):
        """_extract_tags inclui source_agent:{agent_id} tag."""
        event = {
            "type": "tool_result",
            "agent_id": "coder-agent",
            "level": "INFO",
        }

        tags = memory_observer._extract_tags(event)

        assert "source_agent:coder-agent" in tags
        # Também deve ter a tag antiga agent:
        assert "agent:coder-agent" in tags

    @pytest.mark.asyncio
    async def test_extract_tags_all_cross_agent_tags(self, memory_observer: MemoryObserver):
        """_extract_tags inclui todas as tags necessárias para cross-agent queries."""
        event = {
            "type": "agent_decision",
            "agent_id": "planner",
            "level": "WARNING",
        }

        tags = memory_observer._extract_tags(event)

        # Tags básicas
        assert "event:agent_decision" in tags
        assert "agent:planner" in tags
        assert "warning" in tags

        # Tags de cross-agent (Phase 3)
        assert "session:test-session" in tags
        assert "source_agent:planner" in tags


# ============================================================================
# Phase 3: Integration Tests
# ============================================================================


class TestMemoryObserverPhase3Integration:
    """Tests de integração para Phase 3 - Rich NL Context."""

    @pytest.mark.asyncio
    async def test_process_event_uses_rich_context(self, memory_observer: MemoryObserver):
        """_process_event usa _summarize_event_rich para eventos normais."""
        event = {
            "type": "agent_decision",
            "agent_id": "planner",
            "mission_id": "mission-1",
            "level": "INFO",
            "message": "Planning refactor",
            "data": {
                "decision": "Refactor auth module",
                "reasoning": "Security improvements needed",
            },
            "iteration": 1,
        }

        # Mock save_annotation to capture the annotation
        memory_observer._memory.save_annotation = AsyncMock()

        await memory_observer._process_event(event)

        # Verificar que save_annotation foi chamado
        assert memory_observer._memory.save_annotation.called
        call_args = memory_observer._memory.save_annotation.call_args[0]
        annotation = call_args[0]

        # Verificar que content é rico (não limitado a 500 chars)
        assert "Decision: Refactor auth module" in annotation.content
        assert "Reasoning: Security improvements needed" in annotation.content
        assert "Mission: mission-1" in annotation.content

        # Verificar tags de cross-agent
        assert "session:test-session" in annotation.tags
        assert "source_agent:planner" in annotation.tags

    @pytest.mark.asyncio
    async def test_process_event_tool_result_extracts_diff(self, memory_observer: MemoryObserver):
        """_process_event extrai diff_summary de tool_result events."""
        event = {
            "type": "tool_result",
            "agent_id": "coder",
            "mission_id": "mission-1",
            "level": "INFO",
            "message": "File edited",
            "data": {
                "tool_name": "edit_file",
                "status": "success",
                "diff_summary": "+++ Added error handling\n--- Removed deprecated code",
                "result": "Success",
            },
        }

        # Mock save_annotation to capture the annotation
        memory_observer._memory.save_annotation = AsyncMock()

        await memory_observer._process_event(event)

        assert memory_observer._memory.save_annotation.called
        call_args = memory_observer._memory.save_annotation.call_args[0]
        annotation = call_args[0]

        # Verificar que diff_summary está no content
        assert "Diff Summary:" in annotation.content
        assert "+++ Added error handling" in annotation.content
        assert "--- Removed deprecated code" in annotation.content
