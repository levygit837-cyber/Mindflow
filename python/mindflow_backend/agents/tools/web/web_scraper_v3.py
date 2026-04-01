"""WebScraperTool v3 - New Tool System Implementation.

Web scraping with CSS selectors, link extraction, and content parsing using BeautifulSoup.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class WebScraperInput(BaseModel):
    """Input schema for WebScraperTool v3."""

    url: str = Field(
        description="URL to scrape"
    )
    selectors: list[str] = Field(
        default=[],
        description="CSS selectors to extract specific elements"
    )
    headers: dict[str, str] = Field(
        default={},
        description="HTTP headers for the request"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    extract_links: bool = Field(
        default=False,
        description="Extract all links from the page"
    )
    extract_images: bool = Field(
        default=False,
        description="Extract all images from the page"
    )
    extract_text: bool = Field(
        default=True,
        description="Extract clean text content from the page"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def web_scraper_execute(input: WebScraperInput, context: ToolContext) -> dict[str, Any]:
    """Scrape web page content with CSS selectors.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with scraped content or error
    """
    try:
        # Check BeautifulSoup availability
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return {
                "success": False,
                "error": "BeautifulSoup not available. Install with: pip install beautifulsoup4",
                "error_code": "MISSING_DEPENDENCY",
                "url": input.url
            }

        # Fetch page content using HTTP client
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            response = session.get(
                input.url,
                headers=input.headers,
                timeout=input.timeout,
                verify=True
            )
            response.raise_for_status()

        except ImportError:
            return {
                "success": False,
                "error": "requests library not available. Install with: pip install requests",
                "error_code": "MISSING_DEPENDENCY",
                "url": input.url
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to fetch page: {e}",
                "error_code": "FETCH_ERROR",
                "url": input.url
            }

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract data
        result = {
            "url": input.url,
            "title": soup.title.string if soup.title else "",
            "extracted_data": {},
            "links": [],
            "images": [],
            "metadata": {
                "content_type": response.headers.get("content-type"),
                "content_length": len(response.text),
                "status_code": response.status_code
            }
        }

        # Extract text content
        if input.extract_text:
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get clean text
            text = soup.get_text(separator=' ', strip=True)
            # Limit text size
            if len(text) > 50000:
                text = text[:50000] + "\n... Text truncated due to size limit."
            result["content"] = text

        # Extract data by selectors
        for selector in input.selectors:
            elements = soup.select(selector)
            extracted = []
            for element in elements:
                data = {
                    "text": element.get_text(strip=True),
                    "html": str(element)[:1000],  # Limit HTML size
                    "attributes": dict(element.attrs)
                }
                extracted.append(data)
            result["extracted_data"][selector] = extracted

        # Extract links
        if input.extract_links:
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)

                # Convert relative URLs to absolute
                absolute_url = urllib.parse.urljoin(input.url, href)

                links.append({
                    "url": absolute_url,
                    "text": text,
                    "title": link.get('title', ''),
                    "target": link.get('target', '')
                })
            result["links"] = links
            result["links_count"] = len(links)

        # Extract images
        if input.extract_images:
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                alt = img.get('alt', '')
                title = img.get('title', '')

                # Convert relative URLs to absolute
                absolute_url = urllib.parse.urljoin(input.url, src)

                images.append({
                    "url": absolute_url,
                    "alt": alt,
                    "title": title,
                    "width": img.get('width'),
                    "height": img.get('height')
                })
            result["images"] = images
            result["images_count"] = len(images)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Web scraping failed: {e}",
            "error_code": "SCRAPING_ERROR",
            "url": input.url
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


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
