"""Unit tests for TodoListFocusToolV3."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.agents.tools.planning.todo_list_focus_v3 import (
    TodoListFocusInput,
    TodoListFocusToolV3,
    todo_list_focus_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.fixture
def mock_todo_service():
    """Mock TodoPlanningService."""
    service = AsyncMock()
    mock_focused = MagicMock()
    mock_focused.model_dump.return_value = {
        "items": [
            {"description": "Complex task 1", "complexity": "high", "status": "pending"},
            {"description": "Complex task 2", "complexity": "high", "status": "pending"}
        ],
        "total_count": 2
    }
    service.focus_complex_items.return_value = mock_focused
    return service


@pytest.mark.asyncio
async def test_todo_list_focus_basic(mock_tool_context, mock_todo_service):
    """Test basic todo list focus."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_focus_v3.get_todo_planning_service', return_value=mock_todo_service):
        # Set session_id in context
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListFocusInput(
            task_id="task123",
            limit=3
        )

        result = await todo_list_focus_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["task_id"] == "task123"
        assert result["session_id"] == "session123"
        assert result["limit"] == 3
        assert "focused_items" in result


@pytest.mark.asyncio
async def test_todo_list_focus_with_explicit_session_id(mock_tool_context, mock_todo_service):
    """Test focus with explicit session_id."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_focus_v3.get_todo_planning_service', return_value=mock_todo_service):
        input_data = TodoListFocusInput(
            task_id="task123",
            session_id="explicit_session"
        )

        result = await todo_list_focus_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["session_id"] == "explicit_session"


@pytest.mark.asyncio
async def test_todo_list_focus_missing_session_id(mock_tool_context, mock_todo_service):
    """Test focus without session_id."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_focus_v3.get_todo_planning_service', return_value=mock_todo_service):
        input_data = TodoListFocusInput(
            task_id="task123"
        )

        result = await todo_list_focus_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "MISSING_SESSION_ID"


@pytest.mark.asyncio
async def test_todo_list_focus_custom_limit(mock_tool_context, mock_todo_service):
    """Test focus with custom limit."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_focus_v3.get_todo_planning_service', return_value=mock_todo_service):
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListFocusInput(
            task_id="task123",
            limit=10
        )

        result = await todo_list_focus_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["limit"] == 10


@pytest.mark.asyncio
async def test_todo_list_focus_default_limit(mock_tool_context, mock_todo_service):
    """Test focus with default limit."""
    with patch('mindflow_backend.agents.tools.planning.todo_list_focus_v3.get_todo_planning_service', return_value=mock_todo_service):
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListFocusInput(
            task_id="task123"
        )

        result = await todo_list_focus_execute(input_data, mock_tool_context)

        assert result["success"] is True
        assert result["limit"] == 3  # Default


@pytest.mark.asyncio
async def test_todo_list_focus_service_error(mock_tool_context):
    """Test focus with service error."""
    mock_service = AsyncMock()
    mock_service.focus_complex_items.side_effect = Exception("Service error")

    with patch('mindflow_backend.agents.tools.planning.todo_list_focus_v3.get_todo_planning_service', return_value=mock_service):
        mock_tool_context.metadata["session_id"] = "session123"

        input_data = TodoListFocusInput(
            task_id="task123"
        )

        result = await todo_list_focus_execute(input_data, mock_tool_context)

        assert result["success"] is False
        assert result["error_code"] == "FOCUS_ERROR"
