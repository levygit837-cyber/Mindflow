"""Tool for issuing commands to an owned PinchTab browser."""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.schemas.tools.pinchtab_schemas import (
    BrowserCommandAction,
    BrowserCommandRequest,
    PINCHTAB_BROWSER_SCHEMA,
)
from mindflow_backend.services.core import get_pinchtab_fleet_service


class PinchTabBrowserTool(AsyncToolInterface):
    """Expose per-browser browser control actions to the Researcher agent."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "pinchtab_browser"
        self.description = "Control a specific PinchTab browser by browser_id"
        self._schema = PINCHTAB_BROWSER_SCHEMA
        self._fleet_service = get_pinchtab_fleet_service()

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump(mode="json")

    async def execute(
        self,
        browser_id: str,
        action: str,
        session_id: str | None = None,
        payload: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        session_id = session_id or self.session_id
        if not session_id:
            return self._format_result(False, error="session_id is required for PinchTab browser operations")

        request = BrowserCommandRequest(
            session_id=session_id,
            browser_id=browser_id,
            action=BrowserCommandAction(action),
            payload=payload or {},
        )
        response = await self._fleet_service.dispatch_command(request)
        return self._format_result(
            response.success,
            result=response.model_dump(mode="json"),
            error=response.error_message,
        )


__all__ = ["PinchTabBrowserTool"]
