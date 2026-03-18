from __future__ import annotations

from mindflow_backend.schemas.tools.pinchtab_schemas import (
    BrowserCommandAction,
    BrowserCommandRequest,
    BrowserEconomyMode,
    BrowserOwnershipScope,
    BrowserRuntimeState,
    CreateBrowserRequest,
)


def test_create_browser_request_defaults() -> None:
    request = CreateBrowserRequest(session_id="session-1")

    assert request.agent_id == "researcher"
    assert request.economy_mode == BrowserEconomyMode.WARM_PAUSED
    assert request.ownership_scope == BrowserOwnershipScope.RESEARCH_SESSION
    assert request.profile.headless is True
    assert request.profile.stealth is True


def test_browser_command_request_uses_typed_action() -> None:
    command = BrowserCommandRequest(
        session_id="session-1",
        browser_id="browser-1",
        action=BrowserCommandAction.EXTRACT_TEXT,
    )

    assert command.action == BrowserCommandAction.EXTRACT_TEXT
    assert BrowserRuntimeState.WARM_PAUSED.value == "warm_paused"
