"""PinchTab tool interfaces.

Dedicated contracts for the Researcher browser fleet and per-browser handles.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

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
class PinchTabBrowserHandleInterface(Protocol):
    """Per-browser control contract bound to a single browser_id."""

    @property
    def browser_id(self) -> str:
        """Browser identifier bound to this handle."""
        ...

    async def navigate(self, url: str, timeout_seconds: int | None = None) -> BrowserCommandResponse:
        """Navigate the browser to a URL."""
        ...

    async def get_snapshot(
        self,
        filter_interactive: bool = True,
        timeout_seconds: int | None = None,
    ) -> BrowserCommandResponse:
        """Get a snapshot of the current page."""
        ...

    async def extract_text(self, timeout_seconds: int | None = None) -> BrowserCommandResponse:
        """Extract clean text from the current page."""
        ...

    async def click_element(self, element_ref: str, timeout_seconds: int | None = None) -> BrowserCommandResponse:
        """Click an element by reference."""
        ...

    async def fill_input(
        self,
        element_ref: str,
        value: str,
        timeout_seconds: int | None = None,
    ) -> BrowserCommandResponse:
        """Fill an input field."""
        ...

    async def press_key(
        self,
        element_ref: str,
        key: str,
        timeout_seconds: int | None = None,
    ) -> BrowserCommandResponse:
        """Press a key on an element."""
        ...

    async def get_state(self) -> BrowserInstanceState:
        """Return the latest persisted browser state."""
        ...


@runtime_checkable
class PinchTabFleetToolInterface(Protocol):
    """Tool contract for managing the Researcher browser fleet."""

    async def create_browser(self, request: CreateBrowserRequest) -> CreateBrowserResponse:
        """Provision a browser for a research session."""
        ...

    async def list_browsers(self, request: ListBrowsersRequest) -> ListBrowsersResponse:
        """List browsers owned by a research session."""
        ...

    async def get_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Get a single browser state with ownership validation."""
        ...

    async def pause_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Pause a browser runtime."""
        ...

    async def resume_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Resume a browser runtime."""
        ...

    async def close_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Close and deprovision a browser runtime."""
        ...

    async def reconcile_session(self, session_id: str) -> ReconcileFleetResponse:
        """Reconcile persisted state with runtime containers."""
        ...

    async def dispatch(self, request: BrowserCommandRequest) -> BrowserCommandResponse:
        """Dispatch a browser command through the fleet service."""
        ...

    async def get_browser_interface(self, session_id: str, browser_id: str) -> PinchTabBrowserHandleInterface:
        """Return a per-browser control handle."""
        ...


__all__ = [
    "PinchTabBrowserHandleInterface",
    "PinchTabFleetToolInterface",
]
