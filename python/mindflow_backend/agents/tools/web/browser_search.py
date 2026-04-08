"""Browser search tool - exports LightPanda implementation."""

from __future__ import annotations

from mindflow_backend.agents.tools.web.lightpanda_browser_search import (
    LightPandaBrowserSearchTool as BrowserSearchTool,
    get_lightpanda_browser_search_tool as get_browser_search_tool,
)

__all__ = ["BrowserSearchTool", "get_browser_search_tool"]
