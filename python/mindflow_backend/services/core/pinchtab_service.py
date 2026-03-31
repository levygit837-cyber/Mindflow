"""Compatibility facade for PinchTab browser management.

The new implementation is session-scoped and docker-backed via
``PinchTabFleetService``. This facade keeps legacy imports working while
delegating to the fleet service.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.agents.research import (
    BrowserActionResponse,
    BrowserSession,
    IterationType,
    ResearchStatus,
)
from mindflow_backend.schemas.tools.pinchtab_schemas import (
    BrowserCommandAction,
    BrowserCommandRequest,
    CreateBrowserRequest,
    ListBrowsersRequest,
    PinchTabBrowserProfile,
)
from mindflow_backend.services.core.pinchtab_fleet_service import PinchTabFleetService

_logger = get_logger(__name__)

_LEGACY_SESSION_ID = "legacy-pinchtab-session"
_LEGACY_AGENT_ID = "researcher"
_pinchtab_service: PinchTabService | None = None


class PinchTabService:
    """Backwards-compatible API over the session-scoped browser fleet."""

    def __init__(self, fleet_service: PinchTabFleetService | None = None) -> None:
        self.fleet_service = fleet_service or PinchTabFleetService()

    async def create_instance(
        self,
        headless: bool = True,
        stealth: bool = True,
        preferred_port: int | None = None,
        session_id: str = _LEGACY_SESSION_ID,
        agent_id: str = _LEGACY_AGENT_ID,
    ) -> BrowserSession:
        """Create a browser instance using the new fleet service."""
        request = CreateBrowserRequest(
            session_id=session_id,
            agent_id=agent_id,
            profile=PinchTabBrowserProfile(headless=headless, stealth=stealth),
        )
        response = await self.fleet_service.create_browser(request)
        if not response.success or response.browser is None:
            raise RuntimeError(response.error_message or "Failed to create PinchTab browser")
        browser = response.browser
        return BrowserSession(
            browser_id=browser.browser_id,
            instance_id=browser.browser_id,
            tab_id=browser.tab_id or browser.browser_id,
            current_url=browser.current_url,
            status=self._to_research_status(browser.runtime_state.value),
            created_at=browser.created_at or "",
            last_activity=browser.last_activity_at or "",
            actions_completed=browser.actions_completed,
            error_count=browser.error_count,
        )

    async def close_instance(self, browser_id: str, session_id: str = _LEGACY_SESSION_ID) -> bool:
        """Close a browser instance."""
        await self.fleet_service.close_browser(session_id, browser_id)
        return True

    async def cleanup_all(self, session_id: str = _LEGACY_SESSION_ID) -> int:
        """Close all browsers owned by the legacy session."""
        response = await self.fleet_service.list_browsers(
            ListBrowsersRequest(session_id=session_id, agent_id=_LEGACY_AGENT_ID, include_closed=False)
        )
        if not response.success:
            return 0
        for browser in response.browsers:
            await self.fleet_service.close_browser(session_id, browser.browser_id)
        return len(response.browsers)

    async def navigate(self, browser_id: str, url: str, session_id: str = _LEGACY_SESSION_ID) -> BrowserActionResponse:
        return await self._dispatch(
            session_id,
            browser_id,
            IterationType.NAVIGATE,
            BrowserCommandAction.NAVIGATE,
            {"url": url},
        )

    async def extract_text(self, browser_id: str, session_id: str = _LEGACY_SESSION_ID) -> BrowserActionResponse:
        return await self._dispatch(
            session_id,
            browser_id,
            IterationType.EXTRACT,
            BrowserCommandAction.EXTRACT_TEXT,
        )

    async def get_snapshot(
        self,
        browser_id: str,
        filter_interactive: bool = True,
        session_id: str = _LEGACY_SESSION_ID,
    ) -> BrowserActionResponse:
        return await self._dispatch(
            session_id,
            browser_id,
            IterationType.SNAPSHOT,
            BrowserCommandAction.GET_SNAPSHOT,
            {"filter_interactive": filter_interactive},
        )

    async def click_element(
        self,
        browser_id: str,
        element_ref: str,
        session_id: str = _LEGACY_SESSION_ID,
    ) -> BrowserActionResponse:
        return await self._dispatch(
            session_id,
            browser_id,
            IterationType.CLICK,
            BrowserCommandAction.CLICK_ELEMENT,
            {"element_ref": element_ref},
        )

    async def fill_input(
        self,
        browser_id: str,
        element_ref: str,
        value: str,
        session_id: str = _LEGACY_SESSION_ID,
    ) -> BrowserActionResponse:
        return await self._dispatch(
            session_id,
            browser_id,
            IterationType.FILL,
            BrowserCommandAction.FILL_INPUT,
            {"element_ref": element_ref, "value": value},
        )

    async def press_key(
        self,
        browser_id: str,
        element_ref: str,
        key: str,
        session_id: str = _LEGACY_SESSION_ID,
    ) -> BrowserActionResponse:
        return await self._dispatch(
            session_id,
            browser_id,
            IterationType.PRESS,
            BrowserCommandAction.PRESS_KEY,
            {"element_ref": element_ref, "key": key},
        )

    async def list_instances(self, session_id: str = _LEGACY_SESSION_ID) -> list[dict[str, str]]:
        """List managed browsers for the legacy session."""
        response = await self.fleet_service.list_browsers(
            ListBrowsersRequest(session_id=session_id, agent_id=_LEGACY_AGENT_ID, include_closed=False)
        )
        if not response.success:
            return []
        return [browser.model_dump(mode="json") for browser in response.browsers]

    async def get_session_info(
        self,
        browser_id: str,
        session_id: str = _LEGACY_SESSION_ID,
    ) -> BrowserSession | None:
        """Get browser session info for a single managed browser."""
        try:
            browser = await self.fleet_service.get_browser(session_id, browser_id)
        except Exception:
            return None
        return BrowserSession(
            browser_id=browser.browser_id,
            instance_id=browser.browser_id,
            tab_id=browser.tab_id or browser.browser_id,
            current_url=browser.current_url,
            status=self._to_research_status(browser.runtime_state.value),
            created_at=browser.created_at or "",
            last_activity=browser.last_activity_at or "",
            actions_completed=browser.actions_completed,
            error_count=browser.error_count,
        )

    @asynccontextmanager
    async def managed_instance(
        self,
        headless: bool = True,
        stealth: bool = True,
        session_id: str = _LEGACY_SESSION_ID,
    ):
        """Provide a temporary browser instance and always clean it up."""
        browser = await self.create_instance(
            headless=headless,
            stealth=stealth,
            session_id=session_id,
            agent_id=_LEGACY_AGENT_ID,
        )
        try:
            yield browser
        finally:
            await self.close_instance(browser.browser_id, session_id=session_id)

    async def health_check(self, session_id: str = _LEGACY_SESSION_ID) -> bool:
        """Health-check the fleet by listing visible browsers."""
        response = await self.fleet_service.list_browsers(
            ListBrowsersRequest(session_id=session_id, agent_id=_LEGACY_AGENT_ID, include_closed=True)
        )
        return response.success

    async def _dispatch(
        self,
        session_id: str,
        browser_id: str,
        iteration_type: IterationType,
        action: BrowserCommandAction,
        payload: dict | None = None,
    ) -> BrowserActionResponse:
        command = BrowserCommandRequest(
            session_id=session_id,
            browser_id=browser_id,
            action=action,
            payload=payload or {},
        )
        result = await self.fleet_service.dispatch_command(command)
        return BrowserActionResponse(
            success=result.success,
            browser_id=browser_id,
            iteration_type=iteration_type,
            result_data=result.data,
            error_message=result.error_message,
        )

    def _to_research_status(self, runtime_state: str) -> ResearchStatus:
        """Map fleet runtime state into the older research status enum."""
        if runtime_state in {"closed"}:
            return ResearchStatus.COMPLETED
        if runtime_state in {"error", "orphaned"}:
            return ResearchStatus.FAILED
        if runtime_state in {"pending", "provisioning"}:
            return ResearchStatus.PENDING
        return ResearchStatus.IN_PROGRESS


async def get_pinchtab_service() -> PinchTabService:
    """Return a process-wide compatibility facade."""
    global _pinchtab_service
    if _pinchtab_service is None:
        _pinchtab_service = PinchTabService()
    return _pinchtab_service


__all__ = ["PinchTabService", "get_pinchtab_service"]
