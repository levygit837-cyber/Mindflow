"""Web tools for MindFlow agents.

Provides tools for web interactions including browser automation,
HTTP requests, API interactions, and content extraction.
"""

from __future__ import annotations

from .api_client import ApiClientTool

# Compatibility alias
from .browser_search import BrowserSearchTool
from .http_client import HttpClientTool
from .pinchtab_browser import PinchTabBrowserTool

# Browser fleet tools
from .pinchtab_fleet import PinchTabFleetTool

# Web tools (unified from backend)
from .web_scraper import (
    WebScraperTool,
)

__all__ = [
    # Web tools (unified)
    "WebScraperTool",
    
    # PinchTab browser fleet
    "PinchTabFleetTool",
    "PinchTabBrowserTool",

    # Compatibility alias
    "BrowserSearchTool",
    "HttpClientTool",
    "ApiClientTool",
]
