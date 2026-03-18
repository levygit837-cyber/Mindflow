"""Compatibility wrapper for legacy browser_search scope.

The browser-search capability is now implemented through the dedicated
PinchTab browser tool. This wrapper preserves imports and scope aliases.
"""

from __future__ import annotations

from mindflow_backend.agents.tools.web.pinchtab_browser import PinchTabBrowserTool


class BrowserSearchTool(PinchTabBrowserTool):
    """Backward-compatible alias for the new PinchTab browser tool."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "browser_search"
        self.description = "Compatibility alias for pinchtab_browser"


def get_browser_search_tool() -> BrowserSearchTool:
    """Return a compatibility BrowserSearchTool instance."""
    return BrowserSearchTool()


__all__ = ["BrowserSearchTool", "get_browser_search_tool"]
