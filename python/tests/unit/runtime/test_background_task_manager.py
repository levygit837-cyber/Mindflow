from __future__ import annotations

import asyncio

import pytest

from mindflow_backend.runtime.execution.background_task_manager import BackgroundTaskManager
from mindflow_backend.services.orchestration.execution_task_service import ExecutionTaskService


@pytest.mark.asyncio
async def test_background_task_manager_tracks_completion_and_persists_runtime_task(tmp_path) -> None:
    execution_service = ExecutionTaskService()
    manager = BackgroundTaskManager(
        execution_task_service=execution_service,
        output_dir=tmp_path,
    )

    task = await manager.spawn(
        command="python -c \"print('background-finished')\"",
        cwd=str(tmp_path),
        env={},
        description="Background shell test",
        session_id="session-bg",
        task_id="task-bg",
        tool_call_id="tool-call-bg",
    )

    assert task.background_task_id

    for _ in range(20):
        status = await manager.get_status(task.background_task_id)
        if status["status"] != "running":
            break
        await asyncio.sleep(0.05)

    assert status["status"] == "completed"
    overview = await execution_service.get_task_overview("task-bg")
    assert overview["status"] == "completed"


@pytest.mark.asyncio
async def test_background_task_manager_can_kill_running_process(tmp_path) -> None:
    manager = BackgroundTaskManager(output_dir=tmp_path)

    task = await manager.spawn(
        command="sleep 5",
        cwd=str(tmp_path),
        env={},
        description="Killable background shell test",
    )

    kill_result = await manager.kill(task.background_task_id)
    assert kill_result["success"] is True

    status = await manager.get_status(task.background_task_id)
    assert status["status"] == "killed"
