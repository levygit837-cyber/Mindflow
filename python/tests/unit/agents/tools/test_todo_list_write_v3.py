"""Unit tests for TodoListWriteToolV3."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.agents.tools.planning.todo_list_write_v3 import (
    TodoListWriteInput,
    TodoListWriteToolV3,
    todo_list_write_execute,
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
        "items": [],
        "created_at": "2026-04-01T00:00:00"
    }
    service.replace_list.return_value = mock_snapshot
    return service


@pytest.mark.asyncio
async def test_todo_list_write_basic(mock_tool_context, mock_todo_service):
    """Test basic todo list write."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_write_v3.get_todo_planning_service', return_value=mock_todo_service):
        # Set session_id in context
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListWriteInput(
            task_id="task123",
            goal="Complete feature X",
            items=[
                {"description": "Step 1", "status": "pending"},
                {"description": "Step 2", "status": "pending"}
            ]
        )

        result = await todo_list_write_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["task_id"] == "task123"
        assert result["session_id"] == "session123"
        assert "snapshot" in result


@pytest.mark.asyncio
async def test_todo_list_write_with_explicit_session_id(mock_tool_context, mock_todo_service):
    """Test write with explicit session_id."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_write_v3.get_todo_planning_service', return_value=mock_todo_service):
        input_data = TodoListWriteInput(
            task_id="task123",
            goal="Complete feature X",
            items=[],
            session_id="explicit_session"
        )

        result = await todo_list_write_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["session_id"] == "explicit_session"


@pytest.mark.asyncio
async def test_todo_list_write_missing_session_id(mock_tool_context, mock_todo_service):
    """Test write without session_id."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_write_v3.get_todo_planning_service', return_value=mock_todo_service):
        input_data = TodoListWriteInput(
            task_id="task123",
            goal="Complete feature X",
            items=[]
        )

        result = await todo_list_write_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "MISSING_SESSION_ID"


@pytest.mark.asyncio
async def test_todo_list_write_custom_source(mock_tool_context, mock_todo_service):
    """Test write with custom source."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_write_v3.get_todo_planning_service', return_value=mock_todo_service):
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListWriteInput(
            task_id="task123",
            goal="Complete feature X",
            items=[],
            source="custom_planner"
        )

        result = await todo_list_write_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_todo_list_write_empty_items(mock_tool_context, mock_todo_service):
    """Test write with empty items list."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_write_v3.get_todo_planning_service', return_value=mock_todo_service):
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListWriteInput(
            task_id="task123",
            goal="Complete feature X",
            items=[]
        )

        result = await todo_list_write_execute(input_data, mock_tool_context)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_todo_list_write_service_error(mock_tool_context):
    """Test write with service error."""
    mock_service = AsyncMock()
    mock_service.replace_list.side_effect = Exception("Service error")

    with patch('mindflow_backend.agents.tools.planning.todo_list_write_v3.get_todo_planning_service', return_value=mock_service):
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListWriteInput(
            task_id="task123",
            goal="Complete feature X",
            items=[]
        )

        result = await todo_list_write_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "WRITE_ERROR"
