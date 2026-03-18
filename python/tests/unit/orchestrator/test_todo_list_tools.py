from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_todo_list_tools_write_read_and_focus() -> None:
    from mindflow_backend.agents.tools.planning.todo_list import (
        FocusTodosTool,
        ReadTodosTool,
        WriteTodosTool,
    )
    from mindflow_backend.services import get_todo_planning_service

    service = get_todo_planning_service()
    service._lists.clear()
    service._task_index.clear()

    writer = WriteTodosTool()
    writer.session_id = "tool-session"
    result = await writer.execute(
        task_id="tool-task",
        goal="Test tool flow",
        items=[
            {
                "item_id": "first",
                "title": "First",
                "complexity_score": 0.2,
            },
            {
                "item_id": "second",
                "title": "Second",
                "complexity_score": 0.8,
                "dependencies": ["first"],
                "priority": "high",
            },
        ],
        source="planner",
    )

    assert result["success"] is True
    assert result["result"]["summary"]["total_items"] == 2

    reader = ReadTodosTool()
    reader.session_id = "tool-session"
    read_result = await reader.execute(task_id="tool-task")
    assert read_result["result"]["todo_list"]["goal"] == "Test tool flow"

    focus = FocusTodosTool()
    focus.session_id = "tool-session"
    focus_result = await focus.execute(task_id="tool-task", limit=1)
    assert focus_result["result"]["items"][0]["item_id"] == "second"
