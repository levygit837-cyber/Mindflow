from unittest.mock import AsyncMock, patch

import pytest

from mindflow_backend.agents.tools.callable.planning import (
    TodoListFocusInput as CallableTodoListFocusInput,
    TodoListReadInput as CallableTodoListReadInput,
    TodoListWriteInput as CallableTodoListWriteInput,
    todo_list_focus_impl,
    todo_list_read_impl,
    todo_list_write_impl,
)
from mindflow_backend.agents.tools.planning.todo_list import (
    resolve_planning_session_id,
)
from mindflow_backend.agents.tools.planning.todo_list_focus_v3 import (
    TodoListFocusInput,
    todo_list_focus_execute,
)
from mindflow_backend.agents.tools.planning.todo_list_read_v3 import (
    TodoListReadInput,
    todo_list_read_execute,
)
from mindflow_backend.agents.tools.planning.todo_list_write_v3 import (
    TodoListWriteInput,
    todo_list_write_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


def test_resolve_planning_session_id_uses_most_specific_source() -> None:
    assert (
        resolve_planning_session_id(
            session_id="explicit-session",
            tool_session_id="tool-session",
            context_session_id="context-session",
            context_metadata={"session_id": "metadata-session"},
        )
        == "explicit-session"
    )
    assert (
        resolve_planning_session_id(
            tool_session_id="tool-session",
            context_session_id="context-session",
            context_metadata={"session_id": "metadata-session"},
        )
        == "tool-session"
    )
    assert (
        resolve_planning_session_id(
            context_session_id="context-session",
            context_metadata={"session_id": "metadata-session"},
        )
        == "context-session"
    )
    assert (
        resolve_planning_session_id(context_metadata={"session_id": "metadata-session"})
        == "metadata-session"
    )


def test_resolve_planning_session_id_requires_a_session() -> None:
    with pytest.raises(ValueError, match="session_id is required"):
        resolve_planning_session_id()


@pytest.mark.asyncio
async def test_planning_v3_tools_delegate_to_canonical_helpers() -> None:
    context = ToolContext(metadata={"session_id": "context-session"})

    with patch(
        "mindflow_backend.agents.tools.planning.todo_list.read_todo_snapshot",
        new=AsyncMock(return_value=("context-session", {"todo_list": {"task_id": "task-1"}})),
    ) as read_helper:
        read_result = await todo_list_read_execute(
            TodoListReadInput(task_id="task-1"),
            context,
        )

    read_helper.assert_awaited_once()
    assert read_result["success"] is True
    assert read_result["snapshot"]["todo_list"]["task_id"] == "task-1"

    with patch(
        "mindflow_backend.agents.tools.planning.todo_list.write_todo_snapshot",
        new=AsyncMock(return_value=("context-session", {"todo_list": {"task_id": "task-2"}})),
    ) as write_helper:
        write_result = await todo_list_write_execute(
            TodoListWriteInput(task_id="task-2", goal="goal", items=[]),
            context,
        )

    write_helper.assert_awaited_once()
    assert write_result["success"] is True
    assert write_result["snapshot"]["todo_list"]["task_id"] == "task-2"

    with patch(
        "mindflow_backend.agents.tools.planning.todo_list.focus_todo_items",
        new=AsyncMock(return_value=("context-session", {"items": [{"item_id": "x"}]})),
    ) as focus_helper:
        focus_result = await todo_list_focus_execute(
            TodoListFocusInput(task_id="task-3", limit=1),
            context,
        )

    focus_helper.assert_awaited_once()
    assert focus_result["success"] is True
    assert focus_result["focused_items"]["items"][0]["item_id"] == "x"


@pytest.mark.asyncio
async def test_planning_callable_tools_delegate_to_canonical_helpers() -> None:
    context = ToolContext(session_id="callable-session", metadata={})

    with patch(
        "mindflow_backend.agents.tools.planning.todo_list.read_todo_snapshot",
        new=AsyncMock(return_value=("callable-session", {"todo_list": {"task_id": "task-4"}})),
    ) as read_helper:
        read_result = await todo_list_read_impl(
            CallableTodoListReadInput(task_id="task-4"),
            context,
        )

    read_helper.assert_awaited_once()
    assert read_result.success is True
    assert read_result.data["snapshot"]["todo_list"]["task_id"] == "task-4"

    with patch(
        "mindflow_backend.agents.tools.planning.todo_list.write_todo_snapshot",
        new=AsyncMock(return_value=("callable-session", {"todo_list": {"task_id": "task-5"}})),
    ) as write_helper:
        write_result = await todo_list_write_impl(
            CallableTodoListWriteInput(task_id="task-5", goal="goal", items=[]),
            context,
        )

    write_helper.assert_awaited_once()
    assert write_result.success is True
    assert write_result.data["snapshot"]["todo_list"]["task_id"] == "task-5"

    with patch(
        "mindflow_backend.agents.tools.planning.todo_list.focus_todo_items",
        new=AsyncMock(return_value=("callable-session", {"items": [{"item_id": "y"}]})),
    ) as focus_helper:
        focus_result = await todo_list_focus_impl(
            CallableTodoListFocusInput(task_id="task-6", limit=1),
            context,
        )

    focus_helper.assert_awaited_once()
    assert focus_result.success is True
    assert focus_result.data["focused_items"]["items"][0]["item_id"] == "y"
