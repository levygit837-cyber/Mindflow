from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_tasks_api_reads_real_todo_state() -> None:
    from mindflow_backend.api.v1.tasks import router as tasks_router
    from mindflow_backend.services import get_todo_planning_service

    app = FastAPI()
    app.include_router(tasks_router, prefix="/v1")
    client = TestClient(app)

    service = get_todo_planning_service()
    service._lists.clear()
    service._task_index.clear()

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

    task_response = client.get(f"/v1/tasks/{task_id}")
    assert task_response.status_code == 200
    task_payload = task_response.json()["task"]
    assert task_payload["task_id"] == task_id
    assert task_payload["progress_percentage"] > 0

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
