"""Tool for managing session-owned PinchTab browser fleets."""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.schemas.tools.pinchtab_schemas import (
    PINCHTAB_FLEET_SCHEMA,
    CreateBrowserRequest,
    ListBrowsersRequest,
)
from mindflow_backend.services.core import get_pinchtab_fleet_service


class PinchTabFleetTool(AsyncToolInterface):
    """Expose fleet management actions to the Researcher agent."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "pinchtab_fleet"
        self.description = "Manage PinchTab browsers owned by the current research session"
        self._schema = PINCHTAB_FLEET_SCHEMA
        self._fleet_service = get_pinchtab_fleet_service()

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump(mode="json")

    async def execute(self, action: str, session_id: str | None = None, browser_id: str | None = None, payload: dict[str, Any] | None = None, **_: Any) -> dict[str, Any]:
        payload = payload or {}
        session_id = session_id or self.session_id
        if not session_id:
            return self._format_result(False, error="session_id is required for PinchTab fleet operations")

        if action == "create_browser":
            request = CreateBrowserRequest(
                session_id=session_id,
                agent_id=payload.get("agent_id", "researcher"),
                research_session_id=payload.get("research_session_id"),
                browser_id=payload.get("browser_id"),
                profile=payload.get("profile", {}),
                ownership_scope=payload.get("ownership_scope", "research_session"),
                economy_mode=payload.get("economy_mode", "warm_paused"),
                metadata=payload.get("metadata", {}),
            )
            response = await self._fleet_service.create_browser(request)
            return self._format_result(response.success, result=response.model_dump(mode="json"), error=response.error_message)

        if action == "list_browsers":
            request = ListBrowsersRequest(
                session_id=session_id,
                agent_id=payload.get("agent_id", "researcher"),
                include_closed=payload.get("include_closed", False),
            )
            response = await self._fleet_service.list_browsers(request)
            return self._format_result(response.success, result=response.model_dump(mode="json"), error=response.error_message)

        if action == "reconcile_session":
            response = await self._fleet_service.reconcile_session(session_id)
            return self._format_result(response.success, result=response.model_dump(mode="json"), error=response.error_message)

        if not browser_id:
            return self._format_result(False, error=f"browser_id is required for action '{action}'")

        if action == "get_browser":
            browser = await self._fleet_service.get_browser(session_id, browser_id)
            return self._format_result(True, result=browser.model_dump(mode="json"))
        if action == "pause_browser":
            browser = await self._fleet_service.pause_browser(session_id, browser_id)
            return self._format_result(True, result=browser.model_dump(mode="json"))
        if action == "resume_browser":
            browser = await self._fleet_service.resume_browser(session_id, browser_id)
            return self._format_result(True, result=browser.model_dump(mode="json"))
        if action == "close_browser":
            browser = await self._fleet_service.close_browser(session_id, browser_id)
            return self._format_result(True, result=browser.model_dump(mode="json"))
        return self._format_result(False, error=f"Unsupported PinchTab fleet action: {action}")


__all__ = ["PinchTabFleetTool"]
