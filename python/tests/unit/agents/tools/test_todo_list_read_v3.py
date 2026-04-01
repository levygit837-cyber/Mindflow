"""Unit tests for TodoListReadToolV3."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.agents.tools.planning.todo_list_read_v3 import (
    TodoListReadInput,
    TodoListReadToolV3,
    todo_list_read_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.fixture
def mock_todo_service():
    """Mock TodoPlanningService."""
    service = AsyncMock()
    mock_snapshot = MagicMock()
    mock_snapshot.model_dump.return_value = {
        "task_id": "task123",
        "goal": "Test goal",
        "items": [
            {"description": "Step 1", "status": "completed"},
            {"description": "Step 2", "status": "pending"}
        ],
        "created_at": "2026-04-01T00:00:00"
    }
    service.get_list.return_value = mock_snapshot
    return service


@pytest.mark.asyncio
async def test_todo_list_read_basic(mock_tool_context, mock_todo_service):
    """Test basic todo list read."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_read_v3.get_todo_planning_service', return_value=mock_todo_service):
        # Set session_id in context
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListReadInput(
            task_id="task123"
        )

        result = await todo_list_read_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["task_id"] == "task123"
        assert result["session_id"] == "session123"
        assert "snapshot" in result


@pytest.mark.asyncio
async def test_todo_list_read_with_explicit_session_id(mock_tool_context, mock_todo_service):
    """Test read with explicit session_id."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_read_v3.get_todo_planning_service', return_value=mock_todo_service):
        input_data = TodoListReadInput(
            task_id="task123",
            session_id="explicit_session"
        )

        result = await todo_list_read_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["session_id"] == "explicit_session"


@pytest.mark.asyncio
async def test_todo_list_read_missing_session_id(mock_tool_context, mock_todo_service):
    """Test read without session_id."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_read_v3.get_todo_planning_service', return_value=mock_todo_service):
        input_data = TodoListReadInput(
            task_id="task123"
        )

        result = await todo_list_read_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "MISSING_SESSION_ID"


@pytest.mark.asyncio
async def test_todo_list_read_service_error(mock_tool_context):
    """Test read with service error."""
    mock_service = AsyncMock()
    mock_service.get_list.side_effect = Exception("Service error")

    with patch('mindflow_backend.agents.tools.planning.todo_list_read_v3.get_todo_planning_service', return_value=mock_service):
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListReadInput(
            task_id="task123"
        )

        result = await todo_list_read_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "READ_ERROR"
