"""PinchTab service interfaces.

Separates container orchestration, HTTP browser control, and session fleet
ownership into explicit contracts.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mindflow_backend.interfaces.tools.pinchtab import PinchTabBrowserHandleInterface
from mindflow_backend.schemas.tools.pinchtab_schemas import (
    BrowserCommandRequest,
    BrowserCommandResponse,
    BrowserInstanceState,
    CreateBrowserRequest,
    CreateBrowserResponse,
    ListBrowsersRequest,
    ListBrowsersResponse,
    ReconcileFleetResponse,
)


@runtime_checkable
class PinchTabContainerOrchestratorInterface(Protocol):
    """Container lifecycle contract for a single browser runtime."""

    async def create_container(
        self,
        browser_id: str,
        session_id: str,
        agent_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Provision a runtime container and return runtime metadata."""
        ...

    async def inspect_container(self, container_id: str) -> dict[str, Any] | None:
        """Inspect a managed runtime container."""
        ...

    async def pause_container(self, container_id: str) -> None:
        """Pause a managed runtime container."""
        ...

    async def resume_container(self, container_id: str) -> None:
        """Resume a paused runtime container."""
        ...

    async def stop_container(self, container_id: str) -> None:
        """Stop and remove a managed runtime container."""
        ...


@runtime_checkable
class PinchTabBrowserServiceInterface(Protocol):
    """HTTP API contract against a running PinchTab runtime."""

    async def health_check(self, runtime_endpoint: str) -> bool:
        """Return whether a runtime endpoint is healthy."""
        ...

    async def navigate(
        self,
        runtime_endpoint: str,
        tab_id: str,
        url: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Navigate a runtime tab to a URL."""
        ...

    async def get_snapshot(
        self,
        runtime_endpoint: str,
        tab_id: str,
        filter_interactive: bool = True,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Fetch a page snapshot from the runtime."""
        ...

    async def extract_text(
        self,
        runtime_endpoint: str,
        tab_id: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Extract text from the current page."""
        ...

    async def click_element(
        self,
        runtime_endpoint: str,
        tab_id: str,
        element_ref: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Click an element in the browser."""
        ...

    async def fill_input(
        self,
        runtime_endpoint: str,
        tab_id: str,
        element_ref: str,
        value: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Fill an input in the browser."""
        ...

    async def press_key(
        self,
        runtime_endpoint: str,
        tab_id: str,
        element_ref: str,
        key: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Press a key in the browser."""
        ...

    async def get_state(self, runtime_endpoint: str, tab_id: str) -> dict[str, Any]:
        """Fetch generic runtime state for a managed browser."""
        ...


@runtime_checkable
class PinchTabFleetServiceInterface(Protocol):
    """Session-scoped fleet management contract for Researcher browsers."""

    async def create_browser(self, request: CreateBrowserRequest) -> CreateBrowserResponse:
        """Create a managed browser for the session."""
        ...

    async def list_browsers(self, request: ListBrowsersRequest) -> ListBrowsersResponse:
        """List browsers visible to the session."""
        ...

    async def get_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Fetch a single browser state with ownership validation."""
        ...

    async def pause_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Pause a browser runtime."""
        ...

    async def resume_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Resume a browser runtime."""
        ...

    async def close_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Close a browser runtime."""
        ...

    async def dispatch_command(self, request: BrowserCommandRequest) -> BrowserCommandResponse:
        """Execute a single browser command with ownership validation."""
        ...

    async def reconcile_session(self, session_id: str) -> ReconcileFleetResponse:
        """Reconcile persisted browsers for a session."""
        ...

    async def get_browser_interface(self, session_id: str, browser_id: str) -> PinchTabBrowserHandleInterface:
        """Return a bound browser control handle."""
        ...


__all__ = [
    "PinchTabBrowserServiceInterface",
    "PinchTabContainerOrchestratorInterface",
    "PinchTabFleetServiceInterface",
]
