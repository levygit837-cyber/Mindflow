from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_tasks_api_reads_real_todo_state() -> None:
    from mindflow_backend.api.v1.tasks import router as tasks_router
    from mindflow_backend.services import (
        get_execution_task_service,
        get_todo_planning_service,
    )

    app = FastAPI()
    app.include_router(tasks_router, prefix="/v1")
    client = TestClient(app)

    service = get_todo_planning_service()
    execution_service = get_execution_task_service()
    service._lists.clear()
    service._task_index.clear()
    execution_service._executions.clear()
    execution_service._task_index.clear()
    execution_service._task_control.clear()

    session_id = "api-session"
    task_id = "api-task"

    asyncio.run(
        service.replace_list(
            session_id=session_id,
            task_id=task_id,
            goal="Expose planning state",
            source="decomposition_pipeline",
            items=[
                {
                    "item_id": "s1",
                    "title": "Collect planner output",
                    "status": "completed",
                    "complexity_score": 0.3,
                },
                {
                    "item_id": "s2",
                    "title": "Sync task API",
                    "status": "in_progress",
                    "complexity_score": 0.7,
                    "priority": "high",
                },
            ],
        )
    )
    execution = asyncio.run(
        execution_service.start_execution(
            session_id=session_id,
            task_id=task_id,
            item_id="s2",
            execution_key="item:s2",
            execution_type="agent_step",
            description="Resolve active subtask",
        )
    )

    task_response = client.get(f"/v1/tasks/{task_id}")
    assert task_response.status_code == 200
    task_payload = task_response.json()["task"]
    assert task_payload["task_id"] == task_id
    assert task_payload["progress_percentage"] > 0
    assert task_payload["planning_status"] == "in_progress"
    assert task_payload["execution_status"] == "running"

    subtasks_response = client.get(f"/v1/tasks/{task_id}/subtasks")
    assert subtasks_response.status_code == 200
    subtasks_payload = subtasks_response.json()
    assert subtasks_payload["total"] == 2
    assert subtasks_payload["subtasks"][1]["complexity_score"] >= 0.7

    session_response = client.get(f"/v1/tasks/session/{session_id}")
    assert session_response.status_code == 200
    session_payload = session_response.json()
    assert session_payload["total"] == 1
    assert session_payload["tasks"][0]["task_id"] == task_id

    progress_response = client.get(f"/v1/tasks/{task_id}/progress")
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()["progress"]
    assert progress_payload["current_step"] == "Sync task API"

    executions_response = client.get(f"/v1/tasks/{task_id}/executions")
    assert executions_response.status_code == 200
    executions_payload = executions_response.json()
    assert executions_payload["total"] == 1
    assert executions_payload["executions"][0]["execution_task_id"] == execution.execution_task_id
    assert executions_payload["executions"][0]["status"] == "running"

    cancel_response = client.post(
        f"/v1/tasks/{task_id}/cancel",
        json={"reason": "User requested cancel", "force": False},
    )
    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()["cancel_result"]
    assert cancel_payload["killed_executions"] == 1

    cancelled_subtasks = client.get(f"/v1/tasks/{task_id}/subtasks").json()["subtasks"]
    cancelled_statuses = {item["subtask_id"]: item["status"] for item in cancelled_subtasks}
    assert cancelled_statuses["s2"] == "blocked"

    retry_response = client.post(
        f"/v1/tasks/{task_id}/retry",
        json={"retry_subtasks": True, "retry_from_beginning": False, "max_retry_attempts": 3},
    )
    assert retry_response.status_code == 200
    retry_payload = retry_response.json()["retry_result"]
    assert retry_payload["reopened_items"] == ["s2"]

    retried_subtasks = client.get(f"/v1/tasks/{task_id}/subtasks").json()["subtasks"]
    retried_statuses = {item["subtask_id"]: item["status"] for item in retried_subtasks}
    assert retried_statuses["s1"] == "completed"
    assert retried_statuses["s2"] == "pending"
