"""WebScraperTool v3 - Adapter to the canonical web scraper implementation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext

from .web_scraper import WebScraperTool


class WebScraperInput(BaseModel):
    """Input schema for WebScraperTool v3."""

    url: str = Field(description="URL to scrape")
    selectors: list[str] = Field(
        default=[],
        description="CSS selectors to extract specific elements",
    )
    headers: dict[str, str] = Field(
        default={},
        description="HTTP headers for the request",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )
    extract_links: bool = Field(
        default=False,
        description="Extract all links from the page",
    )
    extract_images: bool = Field(
        default=False,
        description="Extract all images from the page",
    )
    extract_text: bool = Field(
        default=True,
        description="Extract clean text content from the page",
    )


def _map_web_scraper_error(error: str) -> str:
    if (
        "BeautifulSoup not available" in error
        or "requests library not available" in error
        or "No module named" in error
    ):
        return "MISSING_DEPENDENCY"
    if "HTTP request failed" in error or "Invalid URL" in error:
        return "FETCH_ERROR"
    return "SCRAPING_ERROR"


async def web_scraper_execute(input: WebScraperInput, context: ToolContext) -> dict[str, Any]:
    """Scrape web page content using the canonical V1 implementation."""
    try:
        response = await WebScraperTool().execute(
            url=input.url,
            selectors=input.selectors,
            headers=input.headers,
            timeout=input.timeout,
            extract_links=input.extract_links,
            extract_images=input.extract_images,
            extract_text=input.extract_text,
        )
    except ImportError as exc:
        return {
            "success": False,
            "error": str(exc),
            "error_code": "MISSING_DEPENDENCY",
            "url": input.url,
        }

    if not response["success"]:
        error = response.get("error", "Web scraping failed")
        return {
            "success": False,
            "error": error,
            "error_code": _map_web_scraper_error(error),
            "url": input.url,
        }

    return {
        "success": True,
        **response["result"],
    }


WebScraperToolV3 = build_tool(
    name="web_scraper",
    description=(
        "Web scraping tool with CSS selector support. "
        "Extracts page title, clean text content, specific elements via CSS selectors, "
        "links, and images. Converts relative URLs to absolute. "
        "Includes automatic retry and size limits for large pages."
    ),
    input_schema=WebScraperInput,
    execute=web_scraper_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
