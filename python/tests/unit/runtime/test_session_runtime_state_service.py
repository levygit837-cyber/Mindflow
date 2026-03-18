from __future__ import annotations

import pytest


class _FakeRuntimeStateBackend:
    def __init__(self) -> None:
        self.saved: dict[str, dict] = {}

    async def save_session_state(self, session_id: str, state: dict) -> dict:
        self.saved[session_id] = state
        return state

    async def load_session_state(self, session_id: str) -> dict | None:
        return self.saved.get(session_id)

    async def list_session_states(self) -> list[dict]:
        return [
            {"session_id": session_id, **state}
            for session_id, state in self.saved.items()
        ]


@pytest.mark.asyncio
async def test_session_runtime_state_service_saves_loads_and_lists_sessions() -> None:
    from mindflow_backend.services.core.session_runtime_state_service import SessionRuntimeStateService

    backend = _FakeRuntimeStateBackend()
    service = SessionRuntimeStateService(backend=backend)

    await service.save_session_state(
        "session-1",
        {
            "todo_planning": {
                "tasks": {
                    "task-1": {"goal": "Keep execution state"}
                }
            }
        },
    )
    await service.save_session_state(
        "session-2",
        {
            "shell_tabs": {
                "tabs": {
                    "tab-a": {"title": "Terminal"}
                }
            }
        },
    )

    loaded = await service.load_session_state("session-1")
    all_states = await service.list_session_states()

    assert loaded["todo_planning"]["tasks"]["task-1"]["goal"] == "Keep execution state"
    assert {state["session_id"] for state in all_states} == {"session-1", "session-2"}
