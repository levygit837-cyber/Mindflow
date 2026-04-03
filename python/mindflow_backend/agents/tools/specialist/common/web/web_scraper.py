"""Compatibility wrapper for the canonical web tool implementations."""

from mindflow_backend.agents.tools.web.web_scraper import (
    ApiClientTool,
    HttpClientTool,
    WebScraperTool,
)

__all__ = ["HttpClientTool", "WebScraperTool", "ApiClientTool"]
