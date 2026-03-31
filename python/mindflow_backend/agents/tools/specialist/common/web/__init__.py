"""Web tools for MindFlow agents.

Provides tools for web interactions including browser automation,
HTTP requests, API interactions, and content extraction.
"""

from __future__ import annotations

from .api_client import ApiClientTool

# Original web tools
from .browser_search import BrowserSearchTool
from .http_client import HttpClientTool

# Web tools (unified from backend)
from .web_scraper import (
    WebScraperTool,
)

__all__ = [
    # Web tools (unified)
    "WebScraperTool",
    
    # Original web tools
    "BrowserSearchTool",
    "HttpClientTool",
    "ApiClientTool",
]
