"""Web tools for MindFlow agents.

Provides tools for web interactions including browser automation,
HTTP requests, API interactions, and content extraction.
"""

from __future__ import annotations

# Web tools v3 (New Tool system - Phase 3 migration)
from .http_client_v3 import (
    HttpClientToolV3,
)
from .web_scraper_v3 import (
    WebScraperToolV3,
)
from .api_client_v3 import (
    ApiClientToolV3,
)

# Web tools v1 (backward compatibility)
from .api_client import ApiClientTool
from .http_client import HttpClientTool
from .web_scraper import (
    WebScraperTool,
)

# Browser tools
from .browser_search import BrowserSearchTool
from .pinchtab_browser import PinchTabBrowserTool
from .pinchtab_fleet import PinchTabFleetTool

__all__ = [
    # Web tools v3 (Phase 3 migration)
    "HttpClientToolV3",
    "WebScraperToolV3",
    "ApiClientToolV3",

    # Web tools v1 (backward compatibility)
    "WebScraperTool",
    "HttpClientTool",
    "ApiClientTool",

    # Browser tools
    "PinchTabFleetTool",
    "PinchTabBrowserTool",
    "BrowserSearchTool",
]
