from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.schemas.tools.pinchtab_schemas import (
    BrowserCommandAction,
    BrowserCommandRequest,
)
from mindflow_backend.services.core.pinchtab_fleet_service import PinchTabFleetService
from mindflow_backend.storage.postgresql.models import BrowserInstance, ResearchSession, utcnow


class _FakeDbSession:
    async def commit(self) -> None:
        return None


class _FakeSessionFactory:
    def __init__(self, db: _FakeDbSession) -> None:
        self.db = db

    def __call__(self) -> "_FakeSessionFactory":
        return self

    async def __aenter__(self) -> _FakeDbSession:
        return self.db

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_dispatch_command_auto_resumes_warm_paused_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    browser = BrowserInstance(
        browser_id="browser-1",
        instance_id="browser-1",
        tab_id="tab-1",
        current_url=None,
        status="active",
        container_id="container-1",
        runtime_endpoint="http://127.0.0.1:9867",
        economy_mode="warm_paused",
        runtime_state="warm_paused",
        last_activity=utcnow(),
    )
    owner = ResearchSession(
        session_id="session-1",
        agent_id="researcher",
        original_query="pinchtab_fleet_session",
        question_type="general",
        complexity_level="simple",
    )
    container = SimpleNamespace(resume_container=AsyncMock())
    browser_service = SimpleNamespace(extract_text=AsyncMock(return_value={"text": "hello from pinchtab"}))
    service = PinchTabFleetService(
        container_orchestrator=container,
        browser_service=browser_service,
        session_factory=_FakeSessionFactory(_FakeDbSession()),
    )

    async def _get_owned_browser(_db, _session_id: str, _browser_id: str):
        return browser, owner

    scheduled: list[tuple[str, str]] = []
    monkeypatch.setattr(service, "_get_owned_browser", _get_owned_browser)
    monkeypatch.setattr(service, "_schedule_idle_pause", lambda session_id, browser_id: scheduled.append((session_id, browser_id)))

    response = await service.dispatch_command(
        BrowserCommandRequest(
            session_id="session-1",
            browser_id="browser-1",
            action=BrowserCommandAction.EXTRACT_TEXT,
        )
    )

    assert response.success is True
    assert browser.runtime_state == "active"
    assert browser.actions_completed == 1
    container.resume_container.assert_awaited_once_with("container-1")
    assert scheduled == [("session-1", "browser-1")]


@pytest.mark.asyncio
async def test_reconcile_session_marks_missing_container_as_orphaned(monkeypatch: pytest.MonkeyPatch) -> None:
    browser = BrowserInstance(
        browser_id="browser-1",
        instance_id="browser-1",
        tab_id="tab-1",
        current_url=None,
        status="active",
        container_id="container-1",
        runtime_endpoint="http://127.0.0.1:9867",
        economy_mode="warm_paused",
        runtime_state="active",
        last_activity=utcnow(),
    )
    owner = ResearchSession(
        session_id="session-1",
        agent_id="researcher",
        original_query="pinchtab_fleet_session",
        question_type="general",
        complexity_level="simple",
    )
    container = SimpleNamespace(inspect_container=AsyncMock(return_value=None))
    service = PinchTabFleetService(
        container_orchestrator=container,
        browser_service=SimpleNamespace(),
        session_factory=_FakeSessionFactory(_FakeDbSession()),
    )

    async def _list_browser_records(_db, _session_id: str, _agent_id: str, include_closed: bool):
        assert include_closed is True
        return [browser]

    async def _get_owner_session(_db, _research_session_id):
        return owner

    monkeypatch.setattr(service, "_list_browser_records", _list_browser_records)
    monkeypatch.setattr(service, "_get_owner_session", _get_owner_session)

    response = await service.reconcile_session("session-1")

    assert response.success is True
    assert response.orphaned_browser_ids == ["browser-1"]
    assert browser.runtime_state == "orphaned"
